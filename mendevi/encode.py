#!/usr/bin/env python3

"""Perfors encoding tests."""

import click
import pathlib
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time

from cutcutcodec.core.analysis.ffprobe import get_slices_metadata
from cutcutcodec.core.analysis.video.metric import compare
from cutcutcodec.core.analysis.video.properties.duration import get_duration_video
import numpy as np
import tqdm

from .g5kpower import G5kPower
from .merge import merge_file
from .profiles import PROFILES
from .rapl import RAPL
from .utils import get_context, unfold_video_files


def _encode_ref(video: pathlib.Path, profile: str, out: pathlib.Path) -> pathlib.Path:
    """Encode the lossless .y4m reference video."""
    ref_file = out / f"{video.stem}_{profile}.y4m"
    if ref_file.exists():
        return ref_file
    assert video.is_file(), f"the given file {video} doesn't exists"
    tmp = ref_file.with_stem(f"{ref_file.stem}_in_process")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-i", str(video),
            "-pix_fmt", PROFILES[profile]["pix_fmt"], "-strict", "-1",
            "-aspect", f"{PROFILES[profile]['shape'][0]}:{PROFILES[profile]['shape'][1]}",  # set square pixels
            "-vf", (
                f"fps={PROFILES[profile]['fps']}[s];[s]"
                f"zscale={PROFILES[profile]['shape'][0]}:{PROFILES[profile]['shape'][1]}:filter=bicubic"
                f":r={PROFILES[profile]['range']}"
                f":p={PROFILES[profile]['primaries']}"
                f":t={PROFILES[profile]['transfere']}"
                f":m={PROFILES[profile]['matrix']}"
                f":agamma=0"
            ),
            "-map", "0:v:0", str(tmp),
        ], check=True)
    except subprocess.CalledProcessError:
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-i", str(video),
            "-pix_fmt", PROFILES[profile]["pix_fmt"], "-strict", "-1",
            "-aspect", f"{PROFILES[profile]['shape'][0]}:{PROFILES[profile]['shape'][1]}",  # set square pixels
            "-vf", (
                f"fps={PROFILES[profile]['fps']}[s];[s]"
                f"zscale={PROFILES[profile]['shape'][0]}:{PROFILES[profile]['shape'][1]}:filter=bicubic"
            ),
            "-map", "0:v:0", str(tmp),
        ], check=True)
    shutil.move(tmp, ref_file)
    return ref_file


def _get_cmd(profile: str, preset: str, points: int) -> tuple[float, list[str]]:
    """Yield the ffmpeg encode cmd."""
    bit = int(re.search(r"(?P<bit>\d+)le", PROFILES[profile]["pix_fmt"] + "8le")["bit"])
    yield from (
        (crf_, cmd)
        for crf_ in np.linspace(63.0, 1.0, points).tolist()
        for cmd in (
            [
                "libx264",
                "-crf", str(round(crf_*51.0/63.0, 1)),
                "-preset", preset,
                "-tune", "ssim",
            ],
            [
                "libx265",
                "-crf", str(round(crf_*51.0/63.0, 1)),
                "-preset", preset,
                "-tune", "ssim",
            ],
            [  # https://wiki.webmproject.org/ffmpeg/vp9-encoding-guide
                "libvpx-vp9",
                "-crf", str(round(crf_)),
                "-speed", {"slow": "0", "medium": "1", "fast": "4"}[preset],
                "-tune", "ssim",
            ],
            [
                "libsvtav1",
                "-crf", str(round(crf_)),
                "-preset", {"slow": "4", "medium": "6", "fast": "8"}[preset],
                "-svtav1-params", "tune=2:film-grain=0",
            ],
            [
                "vvc",
                "-qp", str(round(crf_)),
                "-preset", preset,
                "-qpa", "1",
                "-vvenc-params", f"internalbitdepth={bit}",
            ],
        )
    )


@click.command()
@click.argument("video", type=click.Path())
@click.option(
    "-p", "--profile",
    type=click.Choice(list(PROFILES)),
    required=True,
    help="The video profile.",
)
@click.option(
    "--preset",
    type=click.Choice(["fast", "medium", "slow"]),
    default="medium",
    help="the compression effort"
)
@click.option("-o", "--out", type=click.Path(), help="The output folder.")
@click.option("-r", "--res", type=click.Path(), help="The result json file to be updated.")
def main(video: str, profile: str, preset: str, out: str = None, res: str = None, **kwargs):
    """Mesure the decoding performance.

    Parameters
    ----------
    video : pathlike
        The video file to be transcoded.
    profile : str
        The video profile including resolution, fps and colorspace.
        Details in ``profiles.py``.
    preset : str, default=medium
        The encoding codec effort, in ``fast``, ``medium``, ``slow``.
    out : str, default=./samples/
        The folder in which to write all transcoded videos.
    res : str, default=./encode.json
        The file containing the results.
    points : int, default=32
        The number of rate per codec.
    """
    # verification, preparation
    video = pathlib.Path(video).expanduser()
    assert isinstance(profile, str), profile.__class__.__name__
    assert profile in PROFILES, f"the profile {profile} is not recognized"
    assert preset in {"slow", "medium", "fast"}, f"the preset {preset} is not recognized"
    out = pathlib.Path(out or "samples").expanduser()
    out.mkdir(parents=True, exist_ok=True)
    res = pathlib.Path(res or pathlib.Path.cwd() / "encode.json")

    # lossless transcode reference file with good shape, rate and colorspace in a raw file
    ref_file = _encode_ref(video, profile, out)

    # iterate on different codecs and qualities
    for crf, encoder_cmd in _get_cmd(profile, preset, int(kwargs.get("points", 32))):
        file = out / (re.sub(r"_?-|:|=", "_", "_".join(encoder_cmd)) + f"_{ref_file.stem}.mp4")
        if file.exists():
            continue
        tmp = pathlib.Path(tempfile.gettempdir()) / file.name
        with RAPL(no_fail=True) as rapl:  # optional measure rapl energy
            t_start = time.time()
            process = subprocess.run([  # start encoding
                "ffmpeg", "-y", "-hide_banner",
                "-color_primaries", PROFILES[profile]["primaries"],
                "-color_trc", PROFILES[profile]["transfere"],
                "-colorspace", PROFILES[profile]["matrix"],
                "-color_range", PROFILES[profile]["range"],
                "-i", str(ref_file), "-c:v", *encoder_cmd, str(tmp),
            ], check=True)
            t_stop = time.time()

        # copy result asynchronously
        move_thread = threading.Thread(target=shutil.copy, args=(tmp, file.with_suffix(".tmp")))
        move_thread.start()

        # request to grid5000
        g5k_thread = G5kPower(platform.node(), t_start, t_stop-t_start)
        g5k_thread.start()

        # run all metrics
        metrics = compare(ref_file, tmp, psnr=True, ssim=True, vmaf=True)

        # extract frames informations
        frames = get_slices_metadata(tmp)
        frames = [dict(zip(frames[0][0], d)) for d in frames[1].pop().tolist()]

        # merge and write the result
        stats = {
            "args": process.args,
            "compression_ratio": ref_file.stat().st_size / tmp.stat().st_size,
            "context": get_context(),
            "crf": crf,
            "encode_power": g5k_thread.get(),
            "encode_rapl": rapl,
            "encode_start": t_start, "encode_stop": t_stop, "encode_duration": t_stop - t_start,
            "encoder": encoder_cmd[0],
            "file": ref_file.stem,
            # "frames": frames,
            "preset": preset,
            "profile": profile,
            "size": tmp.stat().st_size,
            "video_duration": get_duration_video(tmp),
            **metrics,
        }
        merge_file(res, {file.name: stats})

        # finalize file move
        move_thread.join()
        tmp.unlink()
        shutil.move(file.with_suffix(".tmp"), file)
