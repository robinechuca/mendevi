"""Perform decoding measures."""

import contextlib
import datetime
import functools
import logging
import pathlib
import shlex
import sqlite3

import cutcutcodec
import numpy as np
import orjson
from context_verbose import Printer
from flufl.lock import Lock

from mendevi.cmd import CmdFFMPEG
from mendevi.convert import filter_best_order
from mendevi.database.serialize import list_to_binary, tensor_to_binary
from mendevi.utils import cp_shm


def decode(vid: pathlib.Path, **kwargs: dict) -> tuple[str, str | None, str, dict[str]]:
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
    assert isinstance(vid, pathlib.Path), vid.__class__.__name__

    with cp_shm(vid, threshold=kwargs["ram"]) as vid_ram:  # copy input video into ram

        # get cmd
        cmd = get_decode_cmd(
            vid_ram, kwargs.get("filter"), kwargs.get("resolution"), kwargs.get("family"),
        )
        if kwargs.get("callback") is None:
            user_cmd = None
        else:
            user_cmd = kwargs["callback"](cmd, **kwargs)
            if isinstance(user_cmd, str):
                user_cmd = shlex.split(user_cmd)
            assert isinstance(user_cmd, list), user_cmd.__class__.__name__

        # display
        prt_cmd = " ".join(map(
            shlex.quote,
            ({str(vid_ram): str(vid_ram.with_name("vid.mp4"))}.get(c, c) for c in user_cmd or cmd),
        ))
        with Printer(prt_cmd, color="green") as prt:
            prt.print(f"input video: {vid_ram}")

            # decode
            log, activity = cmd.run(user_cmd)

            # print
            prt.print(f"avg cpu usage: {activity['ps_core']:.1f} %")
            prt.print(f"avg ram usage: {1e-9*np.mean(activity['ps_ram']):.2g} Go")
            if "rapl_power" in activity:
                prt.print(f"avg rapl power: {activity['rapl_power']:.2g} W")
            if "wattmeter_power" in activity:
                prt.print(f"avg wattmeter power: {activity['wattmeter_power']:.2g} W")

    decoder = [*cmd.decode, None][0]
    return prt_cmd, decoder, log, activity


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
    cmd, decoder, log, activity = decode(vid, **kwargs)

    with (
        Lock(str(database.with_name(".dblock")), lifetime=datetime.timedelta(seconds=600)),
        sqlite3.connect(database) as conn,
    ):
        cursor = conn.cursor()

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
            "dec_decoder": decoder,
            "dec_env_id": env_id,
            "dec_height": kwargs.get("resolution", (None, None))[0],
            "dec_log": log,
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
    resolution: tuple[int, int] | None = None,
    family: str | None = None,
) -> CmdFFMPEG:
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
    family : str, optional
        If provided, force to use a specific decoder type.

    Returns
    -------
    filter : str
        The full ffmpeg decode bash command arguments.

    Examples
    --------
    >>> import cutcutcodec
    >>> from mendevi.decode import get_decode_cmd
    >>> media = cutcutcodec.utils.get_project_root() / "media" / "video" / "intro.webm"
    >>> print(get_decode_cmd(media, additional_filter="", resolution=None))  # doctest: +ELLIPSIS
    ffmpeg -hide_banner -y -loglevel verbose -threads 1 -i /...intro.webm -vf format=rgb24 -f null -
    >>> print(get_decode_cmd(media, additional_filter="", resolution=(480, 720)))
    ffmpeg ... -i ...intro.webm -vf scale=h=480:w=720:sws_flags=bicubic,format=rgb24 -f null -
    >>>

    """
    cmd = CmdFFMPEG(video)
    cmd.general = [*cmd.general, "-threads", "1"]
    cmd.vid_filter = filter_best_order(
        video,
        additional_filter=additional_filter,
        fps=None,
        pix_fmt="rgb24",
        resolution=resolution,
    )
    if family is not None:
        for family_, decoder in available_decoders(
            cutcutcodec.get_codec_video(video), cutcutcodec.get_pix_fmt(video),
        ):
            if family == family_:
                cmd.decode = decoder
                break
        else:
            msg = f"impossible to find a {family} decoder for {video}"
            raise RuntimeError(msg)
    return cmd


@functools.cache
def create_video_sample(codec: str, pix_fmt: str) -> pathlib.Path:
    """Generate a small sample with the given codec and pixel format."""
    sample = pathlib.Path("/dev/shm") / f"{codec}_{pix_fmt}.mp4"
    if sample.exists():
        return sample
    cmd = CmdFFMPEG(
        video="/dev/urandom",
        general=[
            "-y",
            "-f", "rawvideo",
            "-s", "256x256",
            "-pix_fmt", pix_fmt,
            "-r", "1",
            "-to", "2",
        ],
        output=str(sample),
    )
    if (
        encode := {
            "av1": "libsvtav1",
            "h264": "libx264",
        }.get(codec)
    ) is None:
        msg = f"create a sample with the codec {codec} and pix_fmt {pix_fmt} is not supported"
        raise ValueError(msg)
    cmd.encode = encode
    cmd.run()  # create the test file (never fail)
    return sample


@functools.cache
def test_decode_sample_encoder(sample: pathlib.Path, decoder: str) -> bool:
    """Return True if ffmpeg can decode that video."""
    cmd = CmdFFMPEG(video=sample, decode=decoder)
    try:
        cmd.run()
    except RuntimeError:
        return False
    return True


def available_decoders(codec: str, pix_fmt: str) -> tuple[str, str | None]:
    """Yield the ffmpeg encoder to decode the video from an accelerated device."""
    sample = create_video_sample(codec, pix_fmt)

    # general: -hwaccel cuda -hwaccel_output_format cuda
    match codec:
        case "av1":
            candidates = [("cuvid", "av1_cuvid"), ("cpu", "libdav1d"), ("cpu", "libaom-av1")]
        case "h264":
            candidates = [("cuvid", "h264_cuvid"), ("cpu", "h264"), ("cpu", "libopenh264")]
        case "hevc":
            candidates = [("cuvid", "hevc_cuvid"), ("cpu", "hevc")]
        case "vvc":
            candidates = [("cuvid", "vvc_cuvid"), ("cpu", "vvc")]
        case "vp9":
            candidates = [("cuvid", "vp9_cuvid"), ("cpu", "libvpx-vp9"), ("cpu", "vp9")]
        case _:
            logging.getLogger(__name__).info("no decoder tested for the codec %s", codec)
            candidates = []
    for family, decoder in candidates:
        if test_decode_sample_encoder(sample, decoder):
            yield family, decoder
