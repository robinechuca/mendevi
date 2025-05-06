#!/usr/bin/env python3

"""Perform encoding measures."""

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

from .g5kpower import G5kPower, g5kpower
from .merge import merge_file
from .profiles import PROFILES
from .rapl import RAPL
from .utils import get_context, unfold_video_files


def _encode_ref(video: pathlib.Path, profile: str, out: pathlib.Path) -> pathlib.Path:
    """Encode the lossless raw reference video."""
    ref_file = out / f"raw_{video.stem}_{profile}.mkv"  # colorspace metadata not supported by .y4m
    if ref_file.exists():
        return ref_file
    assert video.is_file(), f"the given file {video} doesn't exists"
    tmp = ref_file.with_stem(f"{ref_file.stem}_in_process")
    from cutcutcodec.core.io import read, write
    from cutcutcodec.core.classes.colorspace import Colorspace
    with read(video) as container:
        stream = container.out_select("video")[0]
        write(
            [stream],
            filename=tmp,
            colorspace=Colorspace(
                "y'pbpr", PROFILES[profile]["primaries"], PROFILES[profile]["transfer"]
            ),
            streams_settings=[{
                "encodec": "rawvideo",
                "rate": PROFILES[profile]["fps"],
                "shape": PROFILES[profile]["shape"][::-1],
                "pix_fmt": PROFILES[profile]["pix_fmt"],
            }],
        )
    # subprocess.run([
    #     "ffmpeg", "-y", "-hide_banner",
    #     "-i", str(tmp),
    #     "-color_primaries", PROFILES[profile]["primaries"],
    #     "-color_trc", PROFILES[profile]["transfer"],
    #     "-c", "copy",
    #     str(ref_file),
    # ], check=True)
    shutil.move(tmp, ref_file)
    return ref_file


def _encode_ref_old(video: pathlib.Path, profile: str, out: pathlib.Path) -> pathlib.Path:
    """Encode the lossless raw reference video."""
    ref_file = out / f"raw_{video.stem}_{profile}.mkv"  # colorspace metadata not supported by .y4m
    if ref_file.exists():
        return ref_file
    assert video.is_file(), f"the given file {video} doesn't exists"
    tmp = ref_file.with_stem(f"{ref_file.stem}_in_process")
    cmd_sart = [
        "ffmpeg", "-y", "-hide_banner",
        "-i", str(video),
        "-pix_fmt", PROFILES[profile]["pix_fmt"],
        "-aspect", f"{PROFILES[profile]['shape'][0]}:{PROFILES[profile]['shape'][1]}",  # set square pixels
    ]
    cmd_end = [
        "-c:v", "rawvideo",
        "-map", "0:v:0",
        str(tmp),
    ]
    try:
        subprocess.run([
            *cmd_sart,
            "-vf", (
                f"fps={PROFILES[profile]['fps']}[s];[s]"
                f"zscale={PROFILES[profile]['shape'][0]}:{PROFILES[profile]['shape'][1]}:filter=bicubic"
                f":r={PROFILES[profile]['range']}"
                f":p={PROFILES[profile]['primaries']}"
                f":t={PROFILES[profile]['transfer']}"
                f":m={PROFILES[profile]['matrix']}"
                f":agamma=0"
            ),
            *cmd_end,
        ], check=True)
    except subprocess.CalledProcessError:
        # The options
        # "-color_primaries", PROFILES[profile]["primaries"],
        # "-color_trc", PROFILES[profile]["transfer"],
        # "-colorspace", PROFILES[profile]["matrix"],
        # "-color_range", PROFILES[profile]["range"],
        # are incompatible with zscale
        subprocess.run([
            *cmd_sart,
            "-vf", (
                f"fps={PROFILES[profile]['fps']}[s];[s]"
                f"zscale={PROFILES[profile]['shape'][0]}:{PROFILES[profile]['shape'][1]}:filter=bicubic"
                f":rin={PROFILES['uhd']['range']}"
                f":pin={PROFILES['uhd']['primaries']}"
                f":tin={PROFILES['uhd']['transfer']}"
                f":min={PROFILES['uhd']['matrix']}"
                f":r={PROFILES[profile]['range']}"
                f":p={PROFILES[profile]['primaries']}"
                f":t={PROFILES[profile]['transfer']}"
                f":m={PROFILES[profile]['matrix']}"
                f":agamma=0"
            ),
            *cmd_end,
        ], check=True)
    shutil.move(tmp, ref_file)
    return ref_file


def _get_cmd(profile: str, preset: str, points: int, threads: int) -> tuple[float, list[str]]:
    """Yield the ffmpeg encode cmd."""
    def _linspace(start: float, end: float, nbr: int):
        interval = (end - start) / (nbr + 1)
        return np.linspace(start+interval, start+nbr*interval, nbr).tolist()

    bit = int(re.search(r"(?P<bit>\d+)le", PROFILES[profile]["pix_fmt"] + "8le")["bit"])
    yield from (
        (crf_, cmd)
        for crf_ in _linspace(63.0, 0.0, points)
        for cmd in (
            [  # https://ffmpeg.party/x264/
                "libx264",
                "-crf", str(round(crf_*51.0/63.0, 1)),
                "-preset", preset,
                "-tune", "ssim",
                "-threads", str(threads),
            ],
            [   # https://x265.readthedocs.io/en/master/cli.html
                "libx265",
                "-crf", str(round(crf_*51.0/63.0, 1)),
                "-preset", preset,
                "-tune", "ssim",
                "-x265-params", f"frame-threads={threads}:pools={threads}:wpp={1 if threads != 1 else 0}",
            ],
            [  # https://wiki.webmproject.org/ffmpeg/vp9-encoding-guide
                "libvpx-vp9",
                "-crf", str(round(crf_)),
                "-speed", {"slow": "0", "medium": "1", "fast": "4"}[preset],
                "-tune", "ssim",
                "-row-mt", "1", "-threads", str(threads),
            ],
            [
                "libsvtav1",
                "-crf", str(round(crf_)),
                "-preset", {"slow": "4", "medium": "6", "fast": "8"}[preset],
                "-svtav1-params", f"tune=2:film-grain=0",
                "-threads", str(threads),  # :lp={threads}",
            ],
            [
                "vvc",
                "-qp", str(round(crf_)),
                "-preset", preset,
                "-qpa", "1",
                "-vvenc-params", f"internalbitdepth={bit}",
                "-threads", str(threads),
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
    help="The compression effort (default = medium)."
)
@click.option("-o", "--out", type=click.Path(), help="The output folder.")
@click.option("-r", "--res", type=click.Path(), help="The result json file to be updated.")
@click.option("-n", "--points", type=int, default=32, help="The number of quality point per encoder.")
@click.option("-t", "--threads", type=int, default=8, help="The number of threads used by encoders.")
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
    threads : int, default=8
        The number of threads
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
    threads = int(kwargs.get("threads", 8))
    for crf, encoder_cmd in _get_cmd(profile, preset, int(kwargs.get("points", 32)), threads):
        file = out / (re.sub(r"_?-|:|=", "_", "_".join(encoder_cmd)) + f"_{ref_file.stem}.mp4")
        if file.exists():
            continue
        tmp = pathlib.Path(tempfile.gettempdir()) / file.name

        # measure IDLE
        idle_duration = 10.0  # duration of the idle measure, in second
        with RAPL(no_fail=True) as idle_rapl:
            t_start = time.time()
            time.sleep(idle_duration)
        if idle_rapl is not None:
            del idle_rapl["energy"]
        try:
            idle_wattmeter = g5kpower(platform.node(), t_start, idle_duration)
        except ValueError:
            idle_wattmeter = None
        else:
            del idle_wattmeter["energy"]

        # encode
        with RAPL(no_fail=True) as rapl:  # optional measure rapl energy
            t_start = time.time()
            # subprocess.Popen([
            #     "ffmpeg", "-y", "-hide_banner",
            #     "-i", str(ref_file), "-c:v", *encoder_cmd,
            #     str(tmp),
            # ])
            process = subprocess.run([  # start encoding
                "ffmpeg", "-y", "-hide_banner",
                "-i", str(ref_file), "-c:v", *encoder_cmd,
                str(tmp),
            ], check=True)
            t_stop = time.time()

        # copy result asynchronously
        move_thread = threading.Thread(target=shutil.copy, args=(tmp, file.with_suffix(".tmp")))
        move_thread.start()

        # request to grid5000
        wattmeter_thread = G5kPower(platform.node(), t_start, t_stop-t_start)
        wattmeter_thread.start()

        # run all metrics
        metrics = compare(ref_file, tmp, psnr=True, ssim=True, vmaf=True)

        # extract frames informations
        frames = get_slices_metadata(tmp)
        frames = [dict(zip(frames[0][0], d)) for d in frames[1].pop().tolist()]

        # merge and write the result
        stats = {
            "args": process.args,
            "compression_ratio": ref_file.stat().st_size / tmp.stat().st_size,
            "crf": crf,
            "encode_context": get_context(),
            "encode_idle_rapl": idle_rapl,
            "encode_idle_wattmeter": idle_wattmeter,
            "encode_rapl": rapl,
            "encode_start": t_start, "encode_stop": t_stop, "encode_duration": t_stop - t_start,
            "encode_threads": threads,
            "encode_wattmeter": wattmeter_thread.get(),
            "encoder": encoder_cmd[0],
            "file": ref_file.stem,
            "frames": frames,
            "preset": preset,
            "profile": profile,
            "size": tmp.stat().st_size,
            "video_duration": float(get_duration_video(tmp)),
            **metrics,
        }
        stats["rate"] = 8 * stats["size"] / stats["video_duration"]
        merge_file(res, {file.name: stats})

        # finalize file move
        move_thread.join()
        tmp.unlink()
        shutil.move(file.with_suffix(".tmp"), file)
