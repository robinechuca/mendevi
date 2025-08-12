#!/usr/bin/env python3

"""Perform encoding measures."""

import itertools
import pathlib
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time

import click
import cutcutcodec
import numpy as np
import tqdm

from .g5kpower import G5kPower, g5kpower
from .merge import merge_file
from .profiles import PROFILES
from .rapl import RAPL
from .usage import Usage
from .context import full_context


ENCODERS = ["libx264", "libx265", "libvpx-vp9", "libsvtav1", "vvc"]


def _encode_ref(video: pathlib.Path, profile: str, out: pathlib.Path) -> pathlib.Path:
    """Encode the lossless raw reference video."""
    # colorspace metadata not supported by y4m, nut
    # yuv420p10le not supported by mkv, avi
    # rawvideo failed with flv, obu, thd, vc1, mp4, ismv, dv, mpg, vob, gif, gxf, ogv, webm, y4m
    ref_file = out / f"raw_{video.stem}_{profile}.mkv"
    if ref_file.exists():
        return ref_file
    assert video.is_file(), f"the given file {video} doesn't exists"
    tmp = ref_file.with_stem(f"{ref_file.stem}_in_process")
    with cutcutcodec.read(video) as container:
        stream = container.out_select("video")[0]
        cutcutcodec.write(
            [stream],
            tmp,
            colorspace=cutcutcodec.Colorspace(
                "y'pbpr", PROFILES[profile]["primaries"], PROFILES[profile]["transfer"]
            ),
            # # lossless raw video (no colorspace metadata)
            # streams_settings=[{  # extension .nut for 10 bit support
            #     "encodec": "rawvideo",
            #     "rate": PROFILES[profile]["fps"],
            #     "shape": PROFILES[profile]["shape"][::-1],
            #     "pix_fmt": PROFILES[profile]["pix_fmt"],
            # }],
            # fast lossless compression
            streams_settings=[{  # extension .mkv
                "encodec": "ffv1",
                "rate": PROFILES[profile]["fps"],
                "shape": PROFILES[profile]["shape"][::-1],
                "pix_fmt": PROFILES[profile]["pix_fmt"],
            }],
            # # slow lossless compression
            # streams_settings=[{  # extension .mp4
            #     "encodec": "jpeg2000",
            #     "rate": PROFILES[profile]["fps"],
            #     "shape": PROFILES[profile]["shape"][::-1],
            #     "pix_fmt": PROFILES[profile]["pix_fmt"],
            # }],
            # # very slow
            # streams_settings=[{
            #     "encodec": "libaom-av1",
            #     "rate": PROFILES[profile]["fps"],
            #     "shape": PROFILES[profile]["shape"][::-1],
            #     "pix_fmt": PROFILES[profile]["pix_fmt"],
            #     "options": {"crf": "0", "cpu-used": "8"}, #, "usage": "allintra"},
            # }],
        )
    shutil.move(tmp, ref_file)
    return ref_file


def _get_cmd(
    encoder: str, profile: str, preset: str, crf: float, threads: int
) -> tuple[float, list[str]]:
    """Yield the ffmpeg encode cmd."""
    bit = int(re.search(r"(?P<bit>\d+)le", PROFILES[profile]["pix_fmt"] + "8le")["bit"])

    def libsvtav1_lp(threads: int) -> int:
        """Convert threads in parralel level."""
        # https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/master/Source/Lib/Globals/enc_handle.c#L749
        return {
            1: 1,
            2: 2, 3: 2, 4: 2, 5: 2,
            6: 3, 7: 3, 8: 3, 9: 3, 10: 3,
            11: 4, 12: 4, 13: 4, 14: 4,
            15: 5, 16: 5,
        }.get(threads, 6)

    match encoder:
        case "libx264":
            return [  # https://ffmpeg.party/x264/
                "libx264",
                "-crf", str(round(crf*51.0/63.0, 1)),
                "-preset", preset,
                "-tune", "ssim",
                "-threads", str(threads),
            ]
        case "libx265":
            return [   # https://x265.readthedocs.io/en/master/cli.html
                "libx265",
                "-crf", str(round(crf*51.0/63.0, 1)),
                "-preset", preset,
                "-tune", "ssim",
                "-x265-params",
                f"frame-threads={threads}:pools={threads}:wpp={1 if threads != 1 else 0}",
            ]
        case "libvpx-vp9":
            return [  # https://wiki.webmproject.org/ffmpeg/vp9-encoding-guide
                "libvpx-vp9",
                "-crf", str(round(crf)),
                "-speed", {"slow": "0", "medium": "1", "fast": "4"}[preset],
                "-tune", "ssim",
                "-row-mt", "1", "-threads", str(threads),
            ]
        case "libsvtav1":
            return [
                "libsvtav1",
                "-crf", str(round(crf)),
                "-preset", {"slow": "4", "medium": "6", "fast": "8"}[preset],
                "-svtav1-params", f"film-grain=0:lp={libsvtav1_lp(threads)}",  # tune=2 broken in v3.0.2
                # "-threads", str(threads),
            ]
        case "vvc":
            return [
                "vvc",
                "-qp", str(round(crf)),
                "-preset", preset,
                "-qpa", "1",
                "-vvenc-params", f"internalbitdepth={bit}",
                "-threads", str(threads),
            ]
        case _:
            raise ValueError(f"the encoder {encoder} is not supported")


def _linspace(start: float, end: float, nbr: int):
    """A linspace omitting the both edges."""
    interval = (end - start) / (nbr + 1)
    return np.linspace(start+interval, start+nbr*interval, nbr).tolist()


@click.command()
@click.argument("video", type=click.Path())
@click.option(
    "-p", "--profile",
    type=click.Choice(list(PROFILES)),
    required=True,
    multiple=True,
    help="The video profile.",
)
@click.option(
    "--preset",
    type=click.Choice(["fast", "medium", "slow"]),
    default=["medium"],
    multiple=True,
    help="The compression effort (default = medium).",
)
@click.option(
    "-e", "--encoder",
    type=click.Choice(list(ENCODERS)),
    default=ENCODERS,
    multiple=True,
    help="The encoder name.",
)
@click.option("-o", "--out", type=click.Path(), help="The output folder.")
@click.option("-r", "--res", type=click.Path(), help="The result json file to be updated.")
@click.option(
    "-n", "--points",
    type=int,
    default=32,
    help="The number of quality point per encoder.",
)
@click.option(
    "-t", "--threads",
    type=int,
    default=[8],
    multiple=True,
    help="The number of threads used by encoders.",
)
@click.option("--psnr/--no-psnr", default=True, help="Compute the PSNR or not.")
@click.option("--ssim/--no-ssim", default=True, help="Compute the SSIM or not.")
@click.option("--uvq/--no-uvq", default=True, help="Compute the UVQ or not.")
@click.option("--vmaf/--no-vmaf", default=True, help="Compute the VMAF or not.")
def main(video: str, out: str = None, res: str = None, **kwargs):
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
    out = pathlib.Path(out or "samples").expanduser()
    out.mkdir(parents=True, exist_ok=True)
    res = pathlib.Path(res or pathlib.Path.cwd() / "encode.json")

    # lossless transcode reference file with good shape, rate and colorspace in a raw file
    ref_files = {profile: _encode_ref(video, profile, out) for profile in kwargs["profile"]}

    # iterate on all the parameters
    for profile, threads, preset, crf, encoder in tqdm.tqdm(
        list(itertools.product(
            kwargs["profile"],
            kwargs["threads"],
            kwargs["preset"],
            _linspace(63.0, 0.0, kwargs["points"]),
            kwargs["encoder"],
        )),
        desc="encode",
        dynamic_ncols=True,
        smoothing=1e-2,
        unit="file",
    ):
        encoder_cmd = _get_cmd(encoder, profile, preset, crf, threads)
        file = out / (
            f"{video.stem}_{encoder}_{crf}_{preset}_{threads}_{profile}.mp4"
        )
        if file.exists():
            continue
        tmp = pathlib.Path(tempfile.gettempdir()) / file.name

        # measure IDLE
        idle_duration = 10.0  # duration of the idle measure, in second
        with RAPL(no_fail=True) as idle_rapl, Usage() as idle_usage:
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
        with RAPL(no_fail=True) as rapl, Usage() as usage:  # optional measure rapl energy
            t_start = time.time()
            process = subprocess.run([  # start encoding
                "ffmpeg", "-y", "-hide_banner",
                "-i", str(ref_files[profile]), "-c:v", *encoder_cmd,
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
        if any(kwargs[m] for m in ["psnr", "ssim", "uvq", "vmaf"]):
            metrics = cutcutcodec.compare(
                ref_files[profile],
                tmp,
                psnr=kwargs["psnr"],
                ssim=kwargs["ssim"],
                uvq=kwargs["uvq"],
                vmaf=kwargs["vmaf"],
            )
        else:
            metrics = {}

        # extract frames informations
        frames = cutcutcodec.core.analysis.ffprobe.get_slices_metadata(tmp)
        frames = [dict(zip(frames[0][0], d)) for d in frames[1].pop().tolist()]

        # merge and write the result
        stats = {
            "args": process.args,
            "cmd": encoder_cmd,
            "compression_ratio": ref_files[profile].stat().st_size / tmp.stat().st_size,
            "crf": crf,
            "encode_context": full_context(),
            "encode_idle_rapl": idle_rapl,
            "encode_idle_usage": idle_usage,
            "encode_idle_wattmeter": idle_wattmeter,
            "encode_rapl": rapl,
            "encode_start": t_start, "encode_stop": t_stop, "encode_duration": t_stop - t_start,
            "encode_threads": threads,
            "encode_usage": usage,
            "encode_wattmeter": wattmeter_thread.get(),
            "encoder": encoder,
            "file": ref_files[profile].stem,
            "frames": frames,
            "preset": preset,
            "profile": profile,
            "size": tmp.stat().st_size,
            "video_duration": float(cutcutcodec.get_duration_video(tmp)),
            **metrics,
        }
        stats["rate"] = 8 * stats["size"] / stats["video_duration"]
        merge_file(res, {file.name: stats})

        # finalize file move
        move_thread.join()
        tmp.unlink()
        shutil.move(file.with_suffix(".tmp"), file)
