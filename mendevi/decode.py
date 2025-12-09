"""Perform decoding measures."""

import contextlib
import datetime
import pathlib
import shlex
import sqlite3
import subprocess

import numpy as np
import orjson
from context_verbose import Printer
from flufl.lock import Lock

from mendevi.database.serialize import list_to_binary, tensor_to_binary
from mendevi.measures import Activity
from mendevi.utils import get_resolution


def decode(vid: pathlib.Path, **kwargs: dict) -> tuple[str, dict[str]]:
    """Decode an existing video.

    Parameters
    ----------
    vid : pathlib.Path
        The source video file to be decoded.
    **kwargs : dict
        Transmitted to :py:func:`get_decode_cmd`.

    Returns
    -------
    cmd : str
        The ffmpeg command.
    activity : dict[str]
        The computeur activity during the decoding process.

    """
    cmd = get_decode_cmd(vid, kwargs.get("filter"), kwargs.get("resolution"))
    prt_cmd = " ".join(map(shlex.quote, [{str(vid): "vid.mp4"}.get(c, c) for c in cmd]))
    with Printer(prt_cmd, color="green") as prt:
        prt.print(f"video: {vid.name}")
        with Activity() as activity:
            subprocess.run(cmd, check=True, capture_output=True)

        # print
        prt.print(f"avg cpu usage: {activity['ps_core']:.1f} %")
        prt.print(f"avg ram usage: {1e-9*np.mean(activity['ps_ram']):.2g} Go")
        if "rapl_power" in activity:
            prt.print(f"avg rapl power: {activity['rapl_power']:.2g} W")
        if "wattmeter_power" in activity:
            prt.print(f"avg wattmeter power: {activity['wattmeter_power']:.2g} W")

    return prt_cmd, activity


def decode_and_store(
    database: pathlib.Path,
    env_id: int,
    vid: pathlib.Path,
    **kwargs: dict,
) -> None:
    """Decode a video file and store the result in the database.

    Parameters
    ----------
    database : pathlike
        The path of the existing database to be updated.
    env_id : int
        The primary integer key of the environment.
    vid : pathlib.Path
        The path of the video to be encoded.
    **kwargs
        Transmitted to :py:func:`decode`.

    """
    # decode the video
    cmd, activity = decode(vid, **kwargs)

    with (
        Lock(str(database.with_name(".dblock")), lifetime=datetime.timedelta(seconds=600)),
        sqlite3.connect(database) as sql_database,
    ):
        cursor = sql_database.cursor()

        # fill video table
        with contextlib.suppress(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO t_vid_video (vid_id, vid_name) VALUES (?, ?)",
                (kwargs["dec_vid_id"], vid.name),
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

        # fill decode table
        values = {
            "dec_act_id": act_id,
            "dec_cmd": cmd,
            "dec_env_id": env_id,
            "dec_height": kwargs.get("resolution", (None, None))[0],
            "dec_pix_fmt": "rgb24",
            "dec_vid_id": kwargs["dec_vid_id"],
            "dec_width": kwargs.get("resolution", (None, None))[1],
        }
        keys = list(values)
        cursor.execute(
            f"INSERT INTO t_dec_decode ({', '.join(keys)}) VALUES ({', '.join('?'*len(keys))})",
            [values[k] for k in keys],
        )


def get_decode_cmd(
    video: pathlib.Path,
    additional_filter: str,
    resolution: tuple[int, int] | None,
) -> list[str]:
    """Return the ffmpeg decode cmd.

    Parameters
    ----------
    video : pathlib.Path
        The video to be decoded.
        It is required to know the resolution in order to adapt the filter.
    additional_filter : str
        The additional video filter, (can be an empty string).
    resolution : tuple[int, int], optional
        The new (heigh, width) video shape.

    Returns
    -------
    filter : str
        The full ffmpeg decode bash command arguments.

    Examples
    --------
    >>> import cutcutcodec
    >>> from mendevi.decode import get_decode_cmd
    >>> media = cutcutcodec.utils.get_project_root() / "media" / "video" / "intro.webm"
    >>> get_decode_cmd(media, additional_filter="", resolution=None)  # doctest: +ELLIPSIS
    ['ffmpeg', '-threads', '1', '-i', '.../intro.webm', '-vf', 'format=rgb24', '-f', 'null', '-']
    >>> get_decode_cmd(media, additional_filter="", resolution=(480, 720))
    [..., '-vf', 'scale=h=480:w=720:sws_flags=bicubic,format=rgb24', '-f', 'null', '-']
    >>>

    """
    if resolution is not None:
        assert isinstance(resolution, tuple), resolution.__class__.__name__
        assert len(resolution) == 2, resolution
        assert isinstance(resolution[0], int), resolution
        assert isinstance(resolution[1], int), resolution
        assert (resolution[0], resolution[1]) > (0, 0), resolution

    filters: list[str] = []
    if additional_filter:
        filters.append(additional_filter)
    if resolution is not None and get_resolution(video) != resolution:
        filters.append(f"scale=h={resolution[0]}:w={resolution[1]}:sws_flags=bicubic")
    filters.append("format=rgb24")  # to match monitor pixel conversion
    filters = ",".join(filters)

    # test with "ffmpeg -hwaccels", and see all decoders with "ffmpeg -decoders | grep cuvid"
    # ffmpeg -vsync 0 -hwaccel cuda -hwaccel_output_format cuda -c:v h264_cuvid -i vid.mkv -f null -

    # test if available with "ffmpeg -init_hw_device qsv=hw"
    # test with "ffmpeg -hwaccels", and see all decoders with "ffmpeg -decoders | grep qsv"
    # ffmpeg -hide_banner -hwaccel qsv -hwaccel_output_format qsv
    # -c:v h264_qsv -i vid.mkv -vf hwdownload,format=nv12 -f null -
    # j'ai fait sudo apt install libvpl-tools
    # sudo apt install intel-gpu-tools pour avoir intel_gpu_top
    return ["ffmpeg", "-threads", "1", "-i", str(video), "-vf", filters, "-f", "null", "-"]
