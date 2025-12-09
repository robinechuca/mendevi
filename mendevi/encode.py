"""Perform encoding measures."""

import contextlib
import datetime
import math
import pathlib
import re
import shlex
import shutil
import sqlite3
import subprocess
import tempfile
import uuid

import cutcutcodec
import numpy as np
import orjson
import tqdm
from context_verbose import Printer
from flufl.lock import Lock

from mendevi.convert import get_convert_cmd
from mendevi.database.serialize import list_to_binary, tensor_to_binary
from mendevi.ffmpeg_cmd import (
    _encode_av1_nvenc,
    _encode_av1_vaapi,
    _encode_h264_nvenc,
    _encode_h264_vaapi,
    _encode_hevc_nvenc,
    _encode_hevc_vaapi,
    _encode_librav1e,
    _encode_libsvtav1,
    _encode_libvpx_vp9,
    _encode_libx264,
    _encode_libx265,
    _encode_vp9_vaapi,
    _encode_vvc,
)
from mendevi.measures import Activity
from mendevi.utils import best_profile, compute_video_hash, hash_to_signature

ENCODERS_CMD = {
    "av1_nvenc": _encode_av1_nvenc,
    "av1_vaapi": _encode_av1_vaapi,
    "h264_nvenc": _encode_h264_nvenc,
    "h264_vaapi": _encode_h264_vaapi,
    "hevc_nvenc": _encode_hevc_nvenc,
    "hevc_vaapi": _encode_hevc_vaapi,
    "librav1e": _encode_librav1e,
    "libsvtav1": _encode_libsvtav1,
    "libvpx-vp9": _encode_libvpx_vp9,
    "libx264": _encode_libx264,
    "libx265": _encode_libx265,
    "vp9_vaapi": _encode_vp9_vaapi,
    "vvc": _encode_vvc,
}


def encode(src: pathlib.Path, **kwargs: dict) -> tuple[pathlib.Path, str, dict[str]]:
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
    dst = pathlib.Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}.mp4"

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
            ffmpeg_output = b""
            is_finish = False
            while not is_finish:
                while (
                    match := re.search(
                        br"time=(?P<h>\d+):(?P<m>\d{1,2}):(?P<s>\d{1,2}\.\d*)", ffmpeg_output,
                    )
                ) is None:
                    if not (buff := process.stderr.read(32)):
                        is_finish = True
                        break
                    ffmpeg_output += buff
                else:
                    ffmpeg_output = ffmpeg_output[match.endpos:]
                    elapsed = round(
                        3600.0*float(match["h"]) + 60.0*float(match["m"]) + float(match["s"]),
                        2,
                    )
                    load.total = max(load.total, elapsed)
                    load.update(elapsed-load.n)
            load.close()
            if process.returncode or not dst.stat().st_size:
                dst.unlink(missing_ok=True)
                msg = f"failed to execute {' '.join(map(shlex.quote, cmd))!r}"
                raise RuntimeError(msg)

        # print
        prt.print(f"avg cpu usage: {activity['ps_core']:.1f} %")
        prt.print(f"avg ram usage: {1e-9*np.mean(activity['ps_ram']):.2g} Go")
        if "rapl_power" in activity:
            prt.print(f"avg rapl power: {activity['rapl_power']:.2g} W")
        if "wattmeter_power" in activity:
            prt.print(f"avg wattmeter power: {activity['wattmeter_power']:.2g} W")

        # compute file hash
        signature = hash_to_signature(compute_video_hash(dst, fast=False))
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
    **kwargs: dict,
) -> None:
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
        with contextlib.suppress(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO t_vid_video (vid_id, vid_name) VALUES (?, ?)",
                (kwargs["src_vid_id"], src.name),
            )
        dst_vid_id: bytes = compute_video_hash(dst)
        with contextlib.suppress(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO t_vid_video (vid_id, vid_name) VALUES (?, ?)",
                (dst_vid_id, dst.name),
            )

        # fill activity table
        activity = {
            "act_duration": activity["duration"],
            "act_gpu_dt": list_to_binary(activity.get("gpu_dt", None)),
            "act_gpu_power": tensor_to_binary(activity.get("gpu_powers", None)),
            "act_ps_core": tensor_to_binary(activity["ps_cores"]),
            "act_ps_dt": list_to_binary(activity["ps_dt"]),
            "act_ps_temp": orjson.dumps(
                activity["ps_temp"], option=orjson.OPT_INDENT_2|orjson.OPT_SORT_KEYS,
            ),
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


def get_transcode_cmd(src: pathlib.Path, dst: pathlib.Path, **kwargs: dict) -> list[str]:
    """Return the ffmpeg encode cmd."""
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
    cmd.extend(ENCODERS_CMD[kwargs["encoder"]](**kwargs))
    # mount in RAM: mount -o mode=1777,nosuid,nodev -t tmpfs tmpfs /tmp
    # # https://trac.ffmpeg.org/wiki/Encode/AV1#AMDAMFAV1
    # # https://trac.ffmpeg.org/wiki/Hardware/AMF
    # # https://github.com/GPUOpen-LibrariesAndSDKs/AMF/wiki/GPU%20and%20APU%20HW%20Features%20and%20Support
    # case "h264_amf":  # for AMD GPU
    #     raise NotImplementedError
    # case "av1_amf":  # for AMD GPU
    #     raise NotImplementedError

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
            msg = f"please define a bitrate rule for the profile {profile}"
            raise NotImplementedError(msg)
    mini, maxi = mini // 2, maxi * 2  # apply margin
    mini, maxi = math.log10(float(mini)), math.log10(float(maxi))
    return round(10.0**(maxi-quality*(maxi-mini)))
