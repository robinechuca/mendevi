#!/usr/bin/env python3

"""Perform encoding measures."""

import datetime
import hashlib
import math
import pathlib
import re
import shlex
import shutil
import sqlite3
import subprocess
import tempfile

import cutcutcodec
import numpy as np
import tqdm
from context_verbose import Printer
from flufl.lock import Lock

from mendevi.convert import get_convert_cmd
from mendevi.database.serialize import list_to_binary, tensor_to_binary
from mendevi.measures import Activity
from mendevi.utils import best_profile, compute_video_hash, hash_to_signature

ENCODERS = {"libx264", "libx265", "libvpx-vp9", "libsvtav1", "vvc"}


def encode(src: pathlib.Path, **kwargs) -> tuple[pathlib.Path, str, dict[str]]:
    """Transcode an existing video.

    Parameters
    ----------
    src : pathlib.Path
        The source video file to be transcoded.
    **kwargs : dict
        Transmitted to :py:func:`get_transcode_cmd`.

    Returns
    -------
    dst : pathlib.Path
        The transcoded video path. The stem contains the md5 hash of the file content.
    cmd : str
        The ffmpeg command.
    activity : dict[str]
        The computeur activity during the transcoding process.

    """
    assert isinstance(src, pathlib.Path), src.__class__.__name__
    assert src.is_file(), src

    # find tempfile name
    signature = hashlib.md5(
        bytes(src) + " ".join(str(kwargs[k]) for k in sorted(kwargs)).encode("utf-8"),
    ).hexdigest()
    dst = pathlib.Path(tempfile.gettempdir()) / f"{signature}.mp4"

    # get cmd
    cmd = get_transcode_cmd(src, dst, **kwargs)

    # display
    prt_cmd = " ".join(
        map(shlex.quote, [{str(src): "src.mp4", str(dst): "dst.mp4"}.get(c, c) for c in cmd]),
    )
    with Printer(prt_cmd, color="green") as prt:
        prt.print(f"input video: {src.name}")
        load = tqdm.tqdm(
            dynamic_ncols=True,
            leave=False,
            smoothing=1e-6,
            total=round(float(cutcutcodec.get_duration_video(src)), 2),
            unit="s",
        )

        # transcode
        with Activity() as activity, subprocess.Popen(cmd, stderr=subprocess.PIPE) as process:
            signature = b""
            is_finish = False
            while not is_finish:
                while (
                    match := re.search(
                        br"time=(?P<h>\d+):(?P<m>\d{1,2}):(?P<s>\d{1,2}\.\d*)", signature,
                    )
                ) is None:
                    if not (buff := process.stderr.read(32)):
                        is_finish = True
                        break
                    signature += buff
                else:
                    signature = signature[match.endpos:]
                    elapsed = round(
                        3600.0*float(match["h"]) + 60.0*float(match["m"]) + float(match["s"]),
                        2,
                    )
                    load.total = max(load.total, elapsed)
                    load.update(elapsed-load.n)
            load.close()
            if process.returncode or not dst.stat().st_size:
                dst.unlink(missing_ok=True)
                raise RuntimeError(f"failed to execute {cmd}")

        # print
        prt.print(f"avg cpu usage: {activity['ps_core']:.1f} %")
        prt.print(f"avg ram usage: {1e-9*np.mean(activity['ps_ram']):.2g} Go")
        if "rapl_power" in activity:
            prt.print(f"avg rapl power: {activity['rapl_power']:.2g} W")
        if "wattmeter_power" in activity:
            prt.print(f"avg wattmeter power: {activity['wattmeter_power']:.2g} W")

        # compute file hash
        signature = hash_to_signature(compute_video_hash(dst))
        prt.print(f"output video: sample_{signature}.mp4")

    # move file
    final_dst = src.parent / f"sample_{signature}.mp4"
    if not final_dst.exists():
        shutil.copy(dst, src.parent / f"sample_{signature}_partial.mp4")
        shutil.move(src.parent / f"sample_{signature}_partial.mp4", final_dst)
        final_dst.chmod(0o777)
    dst.unlink()

    return final_dst, prt_cmd, activity


def encode_and_store(
    database: pathlib.Path,
    env_id: int,
    src: pathlib.Path,
    **kwargs,
):
    """Transcode a video file and store the result in the database.

    Parameters
    ----------
    database : pathlike
        The path of the existing database to be updated.
    env_id : int
        The primary integer key of the environment.
    src : pathlib.Path
        The path of the video to be decoded.
    **kwargs
        Transmitted to :py:func:`encode`.

    Examples
    --------
    >>> import pathlib, tempfile
    >>> from mendevi.database.complete import add_environment
    >>> from mendevi.database.create import create_database
    >>> from mendevi.encode import encode_and_store
    >>> src = pathlib.Path("/data/dataset/video/despacito.mp4")
    >>> create_database(database := pathlib.Path(tempfile.mktemp(suffix=".sqlite")))
    >>> env_id = add_environment(database)
    >>> encode_and_store(
    ...     database, env_id, src,
    ...     encoder="libx264", profile="sd", effort="fast", quality=0.5, threads=8
    ... )
    >>> database.unlink()
    >>>

    """
    # transcode the video
    dst, cmd, activity = encode(src, **kwargs)

    with (
        Lock(str(database.with_name(".dblock")), lifetime=datetime.timedelta(seconds=600)),
        sqlite3.connect(database) as sql_database,
    ):
        cursor = sql_database.cursor()

        # fill video table
        try:
            cursor.execute(
                "INSERT INTO t_vid_video (vid_id, vid_name) VALUES (?, ?)",
                (kwargs["src_vid_id"], src.name),
            )
        except sqlite3.IntegrityError:
            pass
        dst_vid_id: bytes = compute_video_hash(dst)
        try:
            cursor.execute(
                "INSERT INTO t_vid_video (vid_id, vid_name) VALUES (?, ?)",
                (dst_vid_id, dst.name),
            )
        except sqlite3.IntegrityError:
            pass

        # fill activity table
        activity = {
            "act_duration": activity["duration"],
            "act_ps_core": tensor_to_binary(activity["ps_cores"]),
            "act_ps_dt": list_to_binary(activity["ps_dt"]),
            "act_ps_ram": list_to_binary(activity["ps_ram"]),
            "act_rapl_dt": list_to_binary(activity.get("rapl_dt", None)),
            "act_rapl_power": list_to_binary(activity.get("rapl_powers", None)),
            "act_start": activity["start"],
            "act_wattmeter_dt": list_to_binary(activity.get("wattmeter_dt", None)),
            "act_wattmeter_power": list_to_binary(activity.get("wattmeter_powers", None)),
        }
        keys = list(activity)
        (act_id,) = cursor.execute(
            (
                f"INSERT INTO t_act_activity ({', '.join(keys)}) "
                f"VALUES ({', '.join('?'*len(keys))}) RETURNING act_id"
            ),
            [activity[k] for k in keys],
        ).fetchone()

        # fill encode table
        values = {
            "enc_act_id": act_id,
            "enc_cmd": cmd,
            "enc_dst_vid_id": dst_vid_id,
            "enc_effort": kwargs["effort"],
            "enc_encoder": kwargs["encoder"],
            "enc_env_id": env_id,
            "enc_fps": float(kwargs["fps"]),
            "enc_height": kwargs["resolution"][0],
            "enc_pix_fmt": kwargs["pix_fmt"],
            "enc_quality": kwargs["quality"],
            "enc_src_vid_id": kwargs["src_vid_id"],
            "enc_threads": kwargs["threads"],
            "enc_mode": kwargs["mode"],
            "enc_width": kwargs["resolution"][1],
        }
        keys = list(values)
        cursor.execute(
            f"INSERT INTO t_enc_encode ({', '.join(keys)}) VALUES ({', '.join('?'*len(keys))})",
            [values[k] for k in keys],
        )


def get_transcode_cmd(src: pathlib.Path, dst: pathlib.Path, **kwargs) -> list[str]:
    """Return the ffmpeg encode cmd."""

    def libsvtav1_lp(threads: int) -> int:
        """Convert threads in parralel level."""
        # https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/master/Source/Lib/Globals/enc_handle.c#L598
        # lp=1 -> threads=1
        # lp=2 -> threads=2
        # lp=3 -> threads=8
        # lp=4 -> threads=12
        # lp=5 -> threads=16
        # lp=6 -> threads=20
        return {  # threads to lp
            1: 1,
            2: 2, 3: 2, 4: 2, 5: 2,
            6: 3, 7: 3, 8: 3, 9: 3, 10: 3,
            11: 4, 12: 4, 13: 4, 14: 4,
            15: 5, 16: 5, 17: 5,
        }.get(threads, 6)

    # header
    cmd: list[str] = ["ffmpeg", "-y", "-i", str(src)]

    # filter
    if (
        filter_cmd := get_convert_cmd(
            src,
            additional_filter=kwargs["filter"],
            fps=kwargs["fps"],
            pix_fmt=kwargs["pix_fmt"],
            resolution=kwargs["resolution"],
        )
    ):
        cmd.extend(["-vf", filter_cmd])

    # transcode
    cmd.append("-c:v")
    match kwargs["encoder"]:
        case "libx264":
            if kwargs["mode"] == "vbr":
                quality = ["-crf", str(round(kwargs["quality"]*51.0, 1))]
            else:
                rate = f"{quality_to_rate(kwargs)}k"
                quality = [  # https://trac.ffmpeg.org/wiki/Encode/H.264#CBRConstantBitRate
                    "-b:v", rate,
                    "-minrate", rate,
                    "-maxrate", rate,
                    "-bufsize", rate,
                    "-x264-params", "nal-hrd=cbr",
                ]
            cmd.extend([  # https://ffmpeg.party/x264/
                "libx264",
                *quality,
                "-preset", kwargs["effort"],
                "-tune", "ssim",
                "-threads", str(kwargs["threads"]), "-thread_type", "frame",
            ])
        case "libx265":
            if kwargs["mode"] == "vbr":
                cmd.extend([   # https://x265.readthedocs.io/en/master/cli.html
                    "libx265",
                    "-crf", str(round(kwargs["quality"]*51.0, 1)),
                    "-preset", kwargs["effort"],
                    "-tune", "ssim",
                    "-x265-params",
                    (
                        f"frame-threads={kwargs['threads']}:"
                        f"pools={kwargs['threads']}:"
                        f"wpp={1 if kwargs['threads'] != 1 else 0}"
                    ),
                ])
            else:
                rate = quality_to_rate(kwargs)
                cmd.extend([   # https://x265.readthedocs.io/en/master/cli.html
                    "libx265",
                    "-b:v", f"{rate}k",
                    "-preset", kwargs["effort"],
                    "-tune", "ssim",
                    "-x265-params",
                    (
                        f"vbv-maxrate={rate}:vbv-bufsize={rate}:"
                        f"frame-threads={kwargs['threads']}:"
                        f"pools={kwargs['threads']}:"
                        f"wpp={1 if kwargs['threads'] != 1 else 0}"
                    ),
                ])
        case "libvpx-vp9":
            # https://trac.ffmpeg.org/wiki/Encode/VP9
            # https://wiki.webmproject.org/ffmpeg/vp9-encoding-guide
            # https://developers.google.com/media/vp9/settings
            if kwargs["mode"] == "vbr":
                quality = ["-crf", str(round(kwargs["quality"]*63.0)), "-b:v", "0"]
            else:
                rate = f"{quality_to_rate(kwargs)}k"
                quality = ["-b:v", rate, "-minrate", rate, "-maxrate", rate, "-lag-in-frames", "0"]
            cmd.extend([
                "libvpx-vp9",
                *quality,
                # in [-16, 16]
                "-speed", {"slow": "-2", "medium": "1", "fast": "8"}[kwargs["effort"]],
                "-tune", "ssim",
                "-row-mt", "0", "-threads", str(kwargs["threads"]),
            ])
        case "libsvtav1":
            if kwargs["mode"] == "vbr":
                cmd.extend([
                    "libsvtav1",
                    "-crf", str(round(kwargs["quality"]*63.0)),
                    "-preset", {"slow": "4", "medium": "6", "fast": "8"}[kwargs["effort"]],
                    # "-tune", "ssim",  # not same result as -svtav1-params tune=2
                    "-svtav1-params", f"film-grain=0:lp={libsvtav1_lp(kwargs['threads'])}:tune=2",
                ])
            else:
                rate = f"{min(100_000, quality_to_rate(kwargs))}k"
                cmd.extend([
                    "libsvtav1",
                    "-b:v", rate, "-minrate", rate, "-bufsize", rate,
                    "-preset", {"slow": "4", "medium": "6", "fast": "8"}[kwargs["effort"]],
                    "-tune", "ssim",  # -svtav1-params tune=2 not supported in cbr
                    "-svtav1-params", f"rc=1:film-grain=0:lp={libsvtav1_lp(kwargs['threads'])}",
                ])
        case "vvc":  # https://github.com/fraunhoferhhi/vvenc/wiki/FFmpeg-Integration
            if kwargs["mode"] == "vbr":
                quality = ["-qp", str(round(kwargs["quality"]*63.0))]
            else:
                rate = quality_to_rate(kwargs)
                quality = ["-b:v", f"{rate}k", "-maxrate", f"{round(1.5*rate)+1}k"]
            bit = int(re.search(r"(?P<bit>\d+)le", kwargs["pix_fmt"] + "8le")["bit"])
            cmd.extend([
                "vvc",
                *quality,
                "-preset", kwargs["effort"],
                "-qpa", "1",
                "-vvenc-params", f"internalbitdepth={bit}",
                "-threads", str(kwargs["threads"]),
            ])
        # mount in RAM: mount -o mode=1777,nosuid,nodev -t tmpfs tmpfs /tmp
        # https://developer.nvidia.com/video-encode-decode-support-matrix
        case "h264_nvenc":
            # time ffmpeg -c:v h264_cuvid -gpu 0 -i sd_h264.mkv -c:v h264_nvenc -f null -
            if kwargs["mode"] == "vbr":
                cmd.extend([
                    "h264_nvenc",  # metre dans le bon ordre
                    # "-pix_fmt", "yuv420p",  # doesn't support 10 bits
                    "-gpu", "0",
                    "-preset", kwargs["quality"],
                    "-rc", "vbr",
                    "-cq", str(round(1.0 + kwargs["quality"]*50.0)),  # [1, 51]
                ])
            else:
                rate = f"{quality_to_rate(kwargs)}k"
                cmd.extend([
                    "h264_nvenc",
                    # "-pix_fmt", "yuv420p",  # doesn't support 10 bits
                    "-gpu", "0",
                    "-preset", kwargs["quality"],
                    "-b:v", rate,
                    "-minrate", rate,
                    "-maxrate", rate,
                    "-bufsize", rate,
                    "-rc", "cbr",
                ])
            raise NotImplementedError
        case "av1_nvenc":
            raise NotImplementedError

    # final
    cmd.append(str(dst))
    return cmd


def quality_to_rate(kwargs: dict[str]) -> int:
    """Return the absolute target bitrate in kbit/s.

    Based on https://twitch-overlay.fr/quelle-connexion-internet-choisir-pour-streamer-sur-twitch/
    and https://bitmovin.com/blog/video-bitrate-streaming-hls-dash/

    You can plot the bitrate with: mendevi plot mendevi.db -x bitrate -y psnr -f 'mode = "vbr"'

    The flow margin is taken to be twice as small and twice as large as the recommendations.
    """
    quality = kwargs["quality"]
    assert isinstance(quality, float), quality.__class__.__name__
    assert 0.0 <= quality <= 1.0, quality
    match (profile := best_profile(*kwargs["resolution"])):
        case "sd":
            mini, maxi = 400, 2100
        case "hd":
            mini, maxi = 1500, 6000
        case "fhd":
            mini, maxi = 3000, 9000
        case "uhd4k":
            mini, maxi = 10000, 51000
        case _:
            raise NotImplementedError(f"please define a bitrate rule for the profile {profile}")
    mini, maxi = mini // 2, maxi * 2  # apply margin
    mini, maxi = math.log10(float(mini)), math.log10(float(maxi))
    return round(10.0**(maxi-quality*(maxi-mini)))
