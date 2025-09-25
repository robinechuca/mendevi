#!/usr/bin/env python3

"""Define the functions that enable values to be extracted from a select query."""

import functools
import numbers
import re

from mendevi.database.serialize import binary_to_list, binary_to_tensor


JOIN: dict[str: dict[str, str]] = {  # join = JOIN[destination_table][source_table]
    "t_vid_video": {
        "t_dec_decode": "JOIN t_vid_video ON t_dec_decode.dec_vid_id = t_vid_video.vid_id",
        "t_enc_encode": "JOIN t_vid_video ON t_enc_encode.enc_src_vid_id = t_vid_video.vid_id",
        "t_met_metric": "JOIN t_vid_video ON t_met_metric.met_dis_vid_id = t_vid_video.vid_id",
    },
    "t_enc_encode": {
        "t_dec_decode": "JOIN t_enc_encode ON t_dec_decode.dec_vid_id = t_enc_encode.enc_dst_vid_id",
    },
    "t_dec_decode": {
        "t_enc_encode": "JOIN t_dec_decode ON t_enc_encode.enc_dst_vid_id = t_dec_decode.dec_vid_id",
    },
    "t_met_metric": {
        "t_vid_video": "JOIN t_met_metric ON t_vid_video.vid_id = t_met_metric.met_dis_vid_id",
        "t_enc_encode": (
            "JOIN t_met_metric ON t_enc_encode.enc_dst_vid_id = t_met_metric.met_dis_vid_id "
            "AND t_enc_encode.enc_src_vid_id = t_met_metric.met_ref_vid_id"
        ),
        "t_dec_decode": "JOIN t_met_metric ON t_dec_decode.dec_vid_id = t_met_metric.met_dis_vid_id",
    },
    "t_env_environment": {
        "t_dec_decode": "JOIN t_env_environment ON t_dec_decode.dec_env_id = t_env_environment.env_id",
        "t_enc_encode": "JOIN t_env_environment ON t_enc_encode.enc_env_id = t_env_environment.env_id",
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
        "t_dec_decode": (
            "JOIN t_enc_encode AS t_enc_from_dec "
            "ON t_dec_decode.dec_vid_id = t_enc_from_dec.enc_dst_vid_id "
            "JOIN t_vid_video AS t_ref_video "
            "ON t_enc_from_dec.enc_src_vid_id = t_ref_video.vid_id"
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
    },
}


class SqlLinker:
    """Allow you to add an SQL query to an extractor."""

    def __init__(self, *select: str):
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
        for src_table in sorted(joins, key=lambda t: (len(joins[t]), t)):  # priority no join
            select_str = f"SELECT {', '.join(self.select)}"
            if len(select_str) >= 80:
                select_str = f"SELECT\n    {',\n    '.join(self.select)}"
            table_str = f"FROM {src_table}"
            if (join_str := "\n".join(re.sub(" ON ", "\n    ON ", j) for j in joins[src_table])):
                sql = f"{select_str}\n{table_str}\n{join_str}"
            else:
                sql = f"{select_str}\n{table_str}"
            queries.append(sql)
        return queries

    def __call__(self, func: callable) -> callable:
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


@SqlLinker("t_enc_encode.enc_vid_id", "t_enc_encode.enc_cmd", "t_vid_video.vid_name")
def extract_enc_scenario(raw: dict[str]) -> str:
    """Return the unique string specific to the encoding scenario.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_env_id" in raw, "Please correct the SQL query."
    assert "enc_cmd" in raw, "Please correct the SQL query."
    assert "vid_name" in raw, "Please correct the SQL query."
    env_id, cmd, vid_name = raw["enc_env_id"], raw["enc_cmd"], raw["vid_name"]
    assert isinstance(env_id, numbers.Integral), env_id.__class__.__name__
    assert isinstance(cmd, str), cmd.__class__.__name__
    assert isinstance(vid_name, str), vid_name.__class__.__name__
    return f"env {env_id}: {cmd.replace('src.mp4', vid_name)}"


@SqlLinker("t_act_activity.act_ps_dt", "t_act_activity.act_ps_core")
def extract_cores(raw: dict[str]) -> float:
    """Return the average cumulative utilisation rate of logical cores.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "act_ps_dt" in raw, "Please correct the SQL query."
    assert "act_ps_core" in raw, "Please correct the SQL query."
    act_ps_dt = binary_to_list(raw["act_ps_dt"])
    act_ps_core = binary_to_tensor(raw["act_ps_core"]).sum(axis=1)
    integral = (act_ps_core * act_ps_dt).sum()  # act_ps_core is already the average on each dt
    average = integral / act_ps_dt.sum()
    return float(average) / 100.0  # normalisation


@SqlLinker("t_act_activity.act_duration")
def extract_act_duration(raw: dict[str]) -> float:
    """Return the video processing activity duration in seconds.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "act_duration" in raw, "Please correct the SQL query."
    act_duration = raw["act_duration"]
    assert isinstance(act_duration, numbers.Real), act_duration.__class__.__name__
    assert act_duration > 0.0, act_duration.__class__.__name__
    return float(act_duration)


@SqlLinker("t_enc_encode.enc_effort")
def extract_effort(raw: dict[str]) -> str:
    """Return the effort provided as a parameter to the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_effort" in raw, "Please correct the SQL query."
    enc_effort = raw["enc_effort"]
    assert isinstance(enc_effort, str), enc_effort.__class__.__name__
    return str(enc_effort)


@SqlLinker("t_enc_encode.enc_threads")
def extract_threads(raw: dict[str]) -> int:
    """Return the number of threads provided as a parameter to the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_threads" in raw, "Please correct the SQL query."
    enc_threads = raw["enc_threads"]
    assert isinstance(enc_threads, numbers.Integral), enc_threads.__class__.__name__
    assert enc_threads >= 1, enc_threads.__class__.__name__
    return int(enc_threads)


@SqlLinker("t_enc_encode.enc_quality")
def extract_quality(raw: dict[str]) -> float:
    """Return the quality level passed to the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_quality" in raw, "Please correct the SQL query."
    enc_quality = raw["enc_quality"]
    assert isinstance(enc_quality, numbers.Real), enc_quality.__class__.__name__
    assert 0.0 <= enc_quality <= 1.0, enc_quality
    return float(enc_quality)


@SqlLinker("t_enc_encode.enc_encoder")
def extract_encoder(raw: dict[str]) -> str:
    """Return the name of the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_encoder" in raw, "Please correct the SQL query."
    enc_encoder = raw["enc_encoder"]
    assert isinstance(enc_encoder, str), enc_encoder.__class__.__name__
    return str(enc_encoder)


@SqlLinker("t_act_activity.act_wattmeter_dt", "t_act_activity.act_wattmeter_power")
def extract_wattmeter_energy(raw: dict[str]) -> float:
    """Return the total energy consumption in Joules.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "act_wattmeter_dt" in raw, "Please correct the SQL query."
    assert "act_wattmeter_power" in raw, "Please correct the SQL query."
    act_dt = binary_to_list(raw["act_wattmeter_dt"])
    act_power = binary_to_list(raw["act_wattmeter_power"])
    integral = 0.5 * ((act_power[:-1] + act_power[1:]) * act_dt).sum()  # trapez method
    return float(integral)


@SqlLinker("t_act_activity.act_wattmeter_dt", "t_act_activity.act_wattmeter_power")
def extract_wattmeter_power(raw: dict[str]) -> float:
    """Return the average power consumption in Watts.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "act_wattmeter_dt" in raw, "Please correct the SQL query."
    assert "act_wattmeter_power" in raw, "Please correct the SQL query."
    act_dt = binary_to_list(raw["act_wattmeter_dt"])
    act_power = binary_to_list(raw["act_wattmeter_power"])
    integral = 0.5 * ((act_power[:-1] + act_power[1:]) * act_dt).sum()  # trapez method
    return float(integral / act_dt.sum())


@SqlLinker("t_vid_video.vid_width")
def extract_profile(raw: dict[str]) -> str:
    """Return the profile of the video.

    The profile is determined based on the width of the video.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    from mendevi.cst.profiles import PROFILES
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "vid_width" in raw, "Please correct the SQL query."
    vid_width = raw["vid_width"]
    assert isinstance(vid_width, numbers.Integral), vid_width.__class__.__name__
    dist_to_profile = {abs(v["resolution"][1]-vid_width): p for p, v in PROFILES.items()}
    return dist_to_profile[min(dist_to_profile)]


@SqlLinker("t_dst_video.vid_duration", "t_dst_video.vid_size")
def extract_bitrate(raw: dict[str]) -> float:
    """Return the video bitrate in bit per second.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "vid_duration" in raw, "Please correct the SQL query."
    assert "vid_size" in raw, "Please correct the SQL query."
    duration, size = raw["vid_duration"], raw["vid_size"]
    assert isinstance(duration, float), duration.__class__.__name__
    assert duration > 0, duration
    assert isinstance(size, int), size.__class__.__name__
    assert size >= 0, size
    return 8.0 * float(size) / duration


@SqlLinker("t_ref_video.enc_vid_name AS ref_vid_name")
def extract_src_vid(raw: dict[str]) -> str:
    """Return the input video name.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    from mendevi.cst.profiles import PROFILES
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "ref_vid_name" in raw, "Please correct the SQL query."
    vid_name = raw["ref_vid_name"]
    assert isinstance(vid_name, str), vid_name.__class__.__name__
    vid_name = re.sub(r"^reference_(\w+)_(?:sd|hd|fhd|uhd4k)\.\w+$", r"\1", vid_name)
    return vid_name


@SqlLinker("t_met_metric.met_psnr")
def extract_psnr(raw: dict[str]) -> float:
    """Return the Peak Signal to Noise Ratio (PSNR).

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "met_psnr" in raw, "Please correct the SQL query."
    psnr = binary_to_list(raw["met_psnr"])
    psnr = psnr.mean()
    return float(psnr)


@SqlLinker("t_met_metric.met_ssim")
def extract_ssim(raw: dict[str]) -> float:
    """Return the Structural Similarity (SSIM).

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "met_ssim" in raw, "Please correct the SQL query."
    ssim = binary_to_list(raw["met_ssim"])
    ssim = ssim.mean()
    return float(ssim)


@SqlLinker("t_met_metric.met_vmaf")
def extract_vmaf(raw: dict[str]) -> float:
    """Return the Video Multi-Method Assessment Fusion (VMAF).

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "met_vmaf" in raw, "Please correct the SQL query."
    vmaf = binary_to_list(raw["met_vmaf"])
    vmaf = vmaf.mean()
    return float(vmaf)


@SqlLinker("t_met_metric.met_lpips_alex", "t_met_metric.met_lpips_vgg")
def extract_lpips(raw: dict[str]) -> float:
    """Return the Learned Perceptual Image Patch Similarity (LPIPS) with alex.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "met_lpips_alex" in raw, "Please correct the SQL query."
    assert "met_lpips_vgg" in raw, "Please correct the SQL query."
    lpips = binary_to_list(raw["met_lpips_vgg"] or raw["met_lpips_alex"])
    lpips = lpips.mean()
    return float(lpips)


@SqlLinker("t_met_metric.met_lpips_alex")
def extract_lpips_alex(raw: dict[str]) -> float:
    """Return the Learned Perceptual Image Patch Similarity (LPIPS) with alex.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "met_lpips_alex" in raw, "Please correct the SQL query."
    lpips = binary_to_list(raw["met_lpips_alex"])
    lpips = lpips.mean()
    return float(lpips)


@SqlLinker("t_met_metric.met_lpips_vgg")
def extract_lpips_vgg(raw: dict[str]) -> float:
    """Return the Learned Perceptual Image Patch Similarity (LPIPS) with vgg.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "met_lpips_vgg" in raw, "Please correct the SQL query."
    lpips = binary_to_list(raw["met_lpips_vgg"])
    lpips = lpips.mean()
    return float(lpips)



