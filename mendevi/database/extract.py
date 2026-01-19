"""Define the functions that enable values to be extracted from a select query."""

import functools
import numbers
import pathlib
import re
import typing

import numpy as np
import orjson

from mendevi.cst.profiles import PROFILES
from mendevi.database.serialize import binary_to_list, binary_to_tensor

JOIN: dict[str: dict[str, str]] = {  # join = JOIN[destination_table][source_table]
    "t_vid_video": {
        "t_dec_decode": "JOIN t_vid_video ON t_dec_decode.dec_vid_id = t_vid_video.vid_id",
        "t_enc_encode": "JOIN t_vid_video ON t_enc_encode.enc_dst_vid_id = t_vid_video.vid_id",
        "t_met_metric": "JOIN t_vid_video ON t_met_metric.met_dis_vid_id = t_vid_video.vid_id",
    },
    "t_enc_encode": {
        "t_dec_decode": (
            # rather "JOIN t_enc_encode ON t_dec_decode.dec_vid_id = t_enc_encode.enc_dst_vid_id"
            # this requets select only one line of t_enc_encode
            "JOIN (\n"
            "    SELECT t_enc_encode.enc_dst_vid_id, MIN(enc_id) AS enc_id_min\n"
            "    FROM t_enc_encode\n"
            "    GROUP BY enc_dst_vid_id\n"
            ") AS t_enc_encode_single_dst_vid_id "
            "ON t_dec_decode.dec_vid_id = t_enc_encode_single_dst_vid_id.enc_dst_vid_id\n"
            "JOIN t_enc_encode ON t_enc_encode.enc_id = t_enc_encode_single_dst_vid_id.enc_id_min"
        ),
    },
    "t_dec_decode": {
        "t_enc_encode": (
            "JOIN t_dec_decode ON t_enc_encode.enc_dst_vid_id = t_dec_decode.dec_vid_id"
        ),
    },
    "t_met_metric": {
        "t_vid_video": "LEFT JOIN t_met_metric ON t_vid_video.vid_id = t_met_metric.met_dis_vid_id",
        "t_enc_encode": (
            "LEFT JOIN t_met_metric ON t_enc_encode.enc_dst_vid_id = t_met_metric.met_dis_vid_id "
            "AND t_enc_encode.enc_src_vid_id = t_met_metric.met_ref_vid_id"
        ),
        "t_dec_decode": (
            "LEFT JOIN t_met_metric ON t_dec_decode.dec_vid_id = t_met_metric.met_dis_vid_id"
        ),
    },
    "t_env_environment": {
        "t_dec_decode": (
            "JOIN t_env_environment ON t_dec_decode.dec_env_id = t_env_environment.env_id"
        ),
        "t_enc_encode": (
            "JOIN t_env_environment ON t_enc_encode.enc_env_id = t_env_environment.env_id"
        ),
    },
    "t_act_activity": {
        "t_dec_decode": "JOIN t_act_activity ON t_dec_decode.dec_act_id = t_act_activity.act_id",
        "t_enc_encode": "JOIN t_act_activity ON t_enc_encode.enc_act_id = t_act_activity.act_id",
    },
    "t_idle": {
        "t_env_environment": (
            "JOIN t_act_activity AS t_idle "
            "ON t_env_environment.env_idle_act_id = t_idle.act_id"
        ),
    },
    "t_ref_video": {  # the reference video
        "t_enc_encode": (
            "JOIN t_vid_video AS t_ref_video "
            "ON t_enc_encode.enc_src_vid_id = t_ref_video.vid_id"
        ),
        "t_dec_decode": (  # to avoid redundency, we may define only atomic steps then link them
            "JOIN (\n"
            "    SELECT t_enc_encode.enc_dst_vid_id, MIN(enc_id) AS enc_id_min\n"
            "    FROM t_enc_encode\n"
            "    GROUP BY enc_dst_vid_id\n"
            ") AS t_enc_encode_single_dst_vid_id_from_dec "
            "ON t_dec_decode.dec_vid_id = t_enc_encode_single_dst_vid_id_from_dec.enc_dst_vid_id\n"
            "JOIN t_enc_encode AS t_enc_from_dec "
            "ON t_enc_from_dec.enc_id = t_enc_encode_single_dst_vid_id_from_dec.enc_id_min\n"
            "JOIN t_vid_video AS t_ref_video "
            "ON t_enc_from_dec.enc_src_vid_id = t_ref_video.vid_id"
        ),
        "t_met_metric": (
            "JOIN t_vid_video AS t_ref_video "
            "ON t_met_metric.met_ref_vid_id = t_ref_video.vid_id"
        ),
        "t_vid_video": (
            "JOIN t_vid_video AS t_ref_video ON t_vid_video.vid_id = t_ref_video.vid_id"
        ),
    },
    "t_dst_video": {  # the transcoded video
        "t_enc_encode": (
            "JOIN t_vid_video AS t_dst_video "
            "ON t_enc_encode.enc_dst_vid_id = t_dst_video.vid_id"
        ),
        "t_dec_decode": (
            "JOIN t_vid_video AS t_dst_video "
            "ON t_dec_decode.dec_vid_id = t_dst_video.vid_id"
        ),
        "t_met_metric": (
            "JOIN t_vid_video AS t_dst_video "
            "ON t_met_metric.met_dis_vid_id = t_dst_video.vid_id"
        ),
        "t_vid_video": (
            "JOIN t_vid_video AS t_dst_video ON t_vid_video.vid_id = t_dst_video.vid_id"
        ),
    },
}
# JOIN["t_ref_video"]["t_dec_decode"] = (  # and example of path
#     f"{JOIN['t_enc_encode']['t_dec_decode']}\n"
#     f"{JOIN['t_ref_video']['t_enc_encode']}"
# )


class SqlLinker:
    """Allow you to add an SQL query to an extractor."""

    def __init__(self, *select: str) -> None:
        """Initialise the linker.

        Parameters
        ----------
        select : args[str]
            The fields to be returned (juste after SELECT), with the optional alias.

        """
        assert all(isinstance(s, str) for s in select), select
        self.select: list[str] = sorted(set(select))

    @property
    def sql(self) -> str:
        """Write the sql request."""
        # find all possible junctions
        dst_tables = {s.split(".")[0] for s in self.select}
        joins: dict[str] = {}
        for src_table in {t for j in JOIN.values() for t in j}:
            join: set[str] = set()
            for dst_table in dst_tables - {src_table}:
                if dst_table not in JOIN:
                    break
                if src_table not in JOIN[dst_table]:
                    break
                join.add(JOIN[dst_table][src_table])
            else:
                joins[src_table] = join

        # put in form the queries
        queries: list[str] = []
        for src_table in sorted(
            joins,
            key=lambda t: (
                len(joins[t]),
                {
                    "t_vid_video": 0,
                    "t_act_activity": 1,
                    "t_met_metric": 2,
                    "t_enc_encode": 3,
                    "t_dec_decode": 4,
                    "t_env_environment": 5,
                }[t],
            ),
        ):  # priority no join
            select_str = f"SELECT {', '.join(self.select)}"
            if len(select_str) >= 80:
                select_str = f"SELECT\n    {',\n    '.join(self.select)}"
            table_str = f"FROM {src_table}"
            if (join_str := "\n".join(
                re.sub(" ON ", "\n    ON ", j) for j in sorted(joins[src_table])
            )):
                sql = f"{select_str}\n{table_str}\n{join_str}"
            else:
                sql = f"{select_str}\n{table_str}"
            queries.append(sql)
        return queries

    def __call__(self, func: typing.Callable) -> typing.Callable:
        """Decorate a function.

        Returns
        -------
        A decorated function with the select.
        The docstring of the decorated function is also modified
        to illustrate the minimal SQL query with an example.

        """
        # set attributes
        func.select = self.select

        # set doctrsing
        doc: list[str] = (func.__doc__ or "").split("\n")
        example = "\nor, alternativaly\n".join(
            (
                "\n"
                ".. code:: sql\n"
                "\n"
                f"    {'\n    '.join(sql.split('\n'))}"
                "\n"
            )
            for sql in self.sql
        )
        doc.insert(1, example)
        func.__doc__ = "\n".join(doc)

        return func


def verif(func: typing.Callable) -> typing.Callable:
    """Perform few verifications."""
    @functools.wraps(func)
    def decorated(raw: dict[str]) -> float:
        assert isinstance(raw, dict), raw.__class__.__name__
        for select in func.select:
            name = select.split(" ")[-1].split(".")[-1]
            assert name in raw, \
                f"correct the SQL query because {select} is missing (in {func.__name__})"
        return func(raw)
    return decorated


@verif
@SqlLinker("t_act_activity.act_duration")
def extract_act_duration(raw: dict[str]) -> float:
    """Return the video processing activity duration in seconds.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (act_duration := raw["act_duration"]) is None:
        return None
    assert isinstance(act_duration, numbers.Real), act_duration.__class__.__name__
    assert act_duration > 0.0, act_duration.__class__.__name__
    return float(act_duration)


@verif
@SqlLinker("t_dst_video.vid_codec")
def extract_codec(raw: dict[str]) -> str:
    """Return the codec name.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (codec := raw["vid_codec"]) is None:
        return None
    assert isinstance(codec, str), codec.__class__.__name__
    return str(codec)


@verif
@SqlLinker("t_act_activity.act_ps_dt", "t_act_activity.act_ps_core")
def extract_cores(raw: dict[str]) -> float:
    """Return the average cumulative utilisation rate of logical cores.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    act_ps_dt, act_ps_core = raw["act_ps_dt"], raw["act_ps_core"]
    if act_ps_dt is None or act_ps_core is None:
        return None
    act_ps_dt = binary_to_list(act_ps_dt)
    act_ps_core = binary_to_tensor(act_ps_core).sum(axis=1)
    integral = (act_ps_core * act_ps_dt).sum()  # act_ps_core is already the average on each dt
    average = integral / act_ps_dt.sum()
    return float(average) / 100.0  # normalisation


@verif
@SqlLinker("t_dec_decode.dec_cmd", "t_vid_video.vid_name")
def extract_decode_cmd(raw: dict[str]) -> str:
    """Return the ffmpeg command used for decoding.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (cmd := raw["dec_cmd"]) is None:
        return None
    vid = raw["vid_name"] or "vid.mp4"
    return cmd.replace("vid.mp4", vid)


@verif
@SqlLinker("t_dec_decode.dec_decoder")
def extract_decoder(raw: dict[str]) -> str:
    """Return name of the decoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (decoder := raw["dec_decoder"]) is None:
        return None
    assert isinstance(decoder, str), decoder.__class__.__name__
    return str(decoder)


@verif
@SqlLinker("t_enc_encode.enc_effort")
def extract_effort(raw: dict[str]) -> str:
    """Return the effort provided as a parameter to the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (enc_effort := raw["enc_effort"]) is None:
        return None
    assert isinstance(enc_effort, str), enc_effort.__class__.__name__
    return str(enc_effort)


@verif
@SqlLinker("t_enc_encode.enc_cmd")
def extract_encode_cmd(raw: dict[str]) -> str:
    """Return the ffmpeg command used for encoding.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (cmd := raw["enc_cmd"]) is None:
        return None
    return cmd


@verif
@SqlLinker("t_enc_encode.enc_encoder")
def extract_encoder(raw: dict[str]) -> str:
    """Return the name of the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (encoder := raw["enc_encoder"]) is None:
        return None
    assert isinstance(encoder, str), encoder.__class__.__name__
    return str(encoder)


@verif
@SqlLinker("t_vid_video.vid_frames")
def extract_frames(raw: dict[str]) -> list[dict]:
    """Return the metadata of each frame.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (frames := raw["vid_frames"]) is None:
        return None
    return orjson.loads(frames)


@verif
@SqlLinker("t_dst_video.vid_gamut")
def extract_gamut(raw: dict[str]) -> str:
    """Return the tristimulus primaries colors name.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (gamut := raw["vid_gamut"]) is None:
        return None
    assert isinstance(gamut, str), gamut.__class__.__name__
    return gamut


@verif
@SqlLinker("t_dst_video.vid_height")
def extract_height(raw: dict[str]) -> int:
    """Return the height of images in pixels.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (height := raw["vid_height"]) is None:
        return None
    return int(height)


@verif
@SqlLinker("t_env_environment.env_hostname")
def extract_hostname(raw: dict[str]) -> str:
    """Return the machine name.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (hostname := raw["env_hostname"]) is None:
        return None
    return str(hostname)


@verif
@SqlLinker("t_met_metric.met_lpips_alex", "t_met_metric.met_lpips_vgg")
def extract_lpips(raw: dict[str]) -> float:
    """Return the Learned Perceptual Image Patch Similarity (LPIPS) with alex.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (lpips := raw["met_lpips_vgg"] or raw["met_lpips_alex"]) is None:
        return None
    return float(np.nanmean(binary_to_list(lpips)))


@verif
@SqlLinker("t_met_metric.met_lpips_alex")
def extract_lpips_alex(raw: dict[str]) -> float:
    """Return the Learned Perceptual Image Patch Similarity (LPIPS) with alex.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (lpips := raw["met_lpips_alex"]) is None:
        return None
    return float(np.nanmean(binary_to_list(lpips)))


@verif
@SqlLinker("t_met_metric.met_lpips_vgg")
def extract_lpips_vgg(raw: dict[str]) -> float:
    """Return the Learned Perceptual Image Patch Similarity (LPIPS) with vgg.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (lpips := raw["met_lpips_vgg"]) is None:
        return None
    return float(np.nanmean(binary_to_list(lpips)))


@verif
@SqlLinker("t_enc_encode.enc_mode")
def extract_mode(raw: dict[str]) -> str:
    """Return the bitrate mode, constant (cbr) or variable (vbr).

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (mode := raw["enc_mode"]) is None:
        return None
    assert isinstance(mode, str), mode.__class__.__name__
    assert mode in {"cbr", "vbr"}, mode
    return mode


@SqlLinker(
    "t_act_activity.act_rapl_dt",
    "t_act_activity.act_rapl_power",
    "t_act_activity.act_wattmeter_dt",
    "t_act_activity.act_wattmeter_power",
)
def extract_powers(raw: dict[str]) -> tuple:
    """Return the interval duration and the average power in each intervals.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert (
        ("act_wattmeter_dt" in raw and "act_wattmeter_power" in raw)
        or ("act_rapl_dt" in raw and "act_rapl_power" in raw)
    ), "Please correct the SQL query."
    act_dt, act_power = raw["act_wattmeter_dt"], raw["act_wattmeter_power"]
    if act_dt is not None and act_power is not None:  # if it comes from wattmeter
        act_dt, act_power = binary_to_list(act_dt), binary_to_list(act_power)
        act_power = 0.5 * (act_power[:-1] + act_power[1:])  # trapez method
    else:  # if it comes from rapl
        act_dt, act_power = raw["act_rapl_dt"], raw["act_rapl_power"]
        if act_dt is None or act_power is None:
            return None
        act_dt, act_power = binary_to_list(act_dt), binary_to_list(act_power)
    return act_dt, act_power


@verif
@SqlLinker("t_met_metric.met_psnr")
def extract_psnr(raw: dict[str]) -> float:
    """Return the Peak Signal to Noise Ratio (PSNR).

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (psnr := raw["met_psnr"]) is None:
        return None
    return float(np.nanmean(binary_to_list(psnr)))


@verif
@SqlLinker("t_enc_encode.enc_quality")
def extract_quality(raw: dict[str]) -> float:
    """Return the quality level passed to the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (enc_quality := raw["enc_quality"]) is None:
        return None
    assert isinstance(enc_quality, numbers.Real), enc_quality.__class__.__name__
    assert 0.0 <= enc_quality <= 1.0, enc_quality
    return float(enc_quality)


@verif
@SqlLinker("t_dst_video.vid_range")
def extract_range(raw: dict[str]) -> str:
    """Return the video encoding color range, 'tv' or 'pc'.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (range_ := raw["vid_range"]) is None:
        return None
    assert isinstance(range_, str), range_.__class__.__name__
    assert range_ in {"pc", "tv"}, range_
    return range_


@verif
@SqlLinker("t_ref_video.vid_name AS ref_vid_name")
def extract_reference_video_stem(raw: dict[str]) -> str:
    """Return the input video compact stem.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (vid_name := raw["ref_vid_name"]) is None:
        return None
    assert isinstance(vid_name, str), vid_name.__class__.__name__
    return re.sub(fr"^reference_([\w.]+?)_(?:{'|'.join(PROFILES)})\.\w+$", r"\1", vid_name)


@verif
@SqlLinker("t_vid_video.vid_rms_sobel")
def extract_rms_sobel(raw: dict[str]) -> str:
    """Return the spacial root mean square sobel gradient complexity.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (comp := raw["vid_rms_sobel"]) is None:
        return None
    return float(np.nanmean(binary_to_list(comp)))


@verif
@SqlLinker("t_vid_video.vid_rms_time_diff")
def extract_rms_time_diff(raw: dict[str]) -> str:
    """Return the temporal root means square time difference complexity.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (comp := raw["vid_rms_time_diff"]) is None:
        return None
    return float(np.nanmean(binary_to_list(comp)))


@verif
@SqlLinker("t_met_metric.met_ssim")
def extract_ssim(raw: dict[str]) -> float:
    """Return the Structural Similarity (SSIM).

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (ssim := raw["met_ssim"]) is None:
        return None
    return float(np.nanmean(binary_to_list(ssim)))


@verif
@SqlLinker("t_act_activity.act_ps_dt", "t_act_activity.act_ps_temp")
def extract_temp(raw: dict[str]) -> float:
    """Return the average temperature in C.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    act_ps_dt, act_ps_temp = raw["act_ps_dt"], raw["act_ps_temp"]
    if act_ps_dt is None or act_ps_temp is None:
        return None
    act_ps_dt = binary_to_list(act_ps_dt)
    act_ps_temp = orjson.loads(act_ps_temp)
    avg_temp = sum(np.asarray(tps, act_ps_dt.dtype) for tps in act_ps_temp.values())
    integral = (avg_temp * act_ps_dt).sum()
    average = integral / (act_ps_dt.sum() * len(act_ps_temp))
    return float(average)


@verif
@SqlLinker("t_enc_encode.enc_threads")
def extract_threads(raw: dict[str]) -> int:
    """Return the number of threads provided as a parameter to the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (threads := raw["enc_threads"]) is None:
        return None
    assert isinstance(threads, numbers.Integral), threads.__class__.__name__
    assert threads >= 1, threads.__class__.__name__
    return int(threads)


@verif
@SqlLinker("t_dst_video.vid_eotf")
def extract_transfer(raw: dict[str]) -> str:
    """Return the non-linear transfer function name.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (transfer := raw["vid_eotf"]) is None:
        return None
    assert isinstance(transfer, str), transfer.__class__.__name__
    return transfer


@verif
@SqlLinker("t_dst_video.vid_duration")
def extract_video_duration(raw: dict[str]) -> float:
    """Return the video duration in seconds.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (duration := raw["vid_duration"]) is None:
        return None
    assert isinstance(duration, numbers.Real), duration.__class__.__name__
    return float(duration)


@verif
@SqlLinker("t_vid_video.vid_id")
def extract_video_hash(raw: dict[str]) -> str:
    """Return the hexadecimal md5 video file checksum.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    return raw["vid_id"].hex()


@verif
@SqlLinker("t_vid_video.vid_name")
def extract_video_name(raw: dict[str]) -> str:
    """Return the full video basename.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (vid_name := raw["vid_name"]) is None:
        return None
    assert isinstance(vid_name, str), vid_name.__class__.__name__
    return pathlib.Path(vid_name).name


@verif
@SqlLinker("t_dst_video.vid_size")
def extract_video_size(raw: dict[str]) -> int:
    """Return the total video file size in bytes.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (size := raw["vid_size"]) is None:
        return None
    assert isinstance(size, numbers.Integral), size.__class__.__name__
    return int(size)


@verif
@SqlLinker("t_met_metric.met_vmaf")
def extract_vmaf(raw: dict[str]) -> float:
    """Return the Video Multi-Method Assessment Fusion (VMAF).

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (vmaf := raw["met_vmaf"]) is None:
        return None
    return float(np.nanmean(binary_to_list(vmaf)))


@verif
@SqlLinker("t_dst_video.vid_width")
def extract_width(raw: dict[str]) -> int:
    """Return the width of images in pixels.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    """
    if (width := raw["vid_width"]) is None:
        return None
    return int(width)
