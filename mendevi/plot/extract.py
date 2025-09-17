#!/usr/bin/env python3

"""Define the functions that enable values to be extracted from a select query."""

import functools
import numbers
import re

from mendevi.database.serialize import binary_to_list, binary_to_tensor


class SqlLinker:
    """Allow you to add an SQL query to an extractor."""

    def __init__(self, select: list[str], table: str, join: list[str]):
        """Initialise the linker.

        Parameters
        ----------
        select : list[str]
            The field to be returned (juste after SELECT), with the optional alias.
        table : str
            The data recovery table name, define after the FROM keyword.
        join : list[str]
            The joins, defined after the JOIN keyword.
        """
        # clean inputs
        self.select = [re.sub(r"\s+", " ", s) for s in select]
        self.table = re.sub(r"\s+", " ", table)
        self.join = [re.sub(r"\s+", " ", j) for j in join]

    @property
    def sql(self) -> str:
        """Write the sql request."""
        select_str = f"SELECT {', '.join(self.select)}"
        if len(select_str) >= 80:
            select_str = f"SELECT\n    {',\n    '.join(self.select)}"
        table_str = f"FROM {self.table}"
        if (join_str := "\n".join(re.sub(" ON ", "\n    ON ", j) for j in self.join)):
            sql = f"{select_str}\n{table_str}\n{join_str}"
        else:
            sql = f"{select_str}\n{table_str}"
        return sql

    def __call__(self, func: callable) -> callable:
        """Decorate a function.

        Returns
        -------
        A decorated function with the select, table, and join parameters.
        The docstring of the decorated function is also modified
        to illustrate the minimal SQL query with an example.
        """
        # set attributes
        func.select = self.select
        func.table = self.table
        func.join = self.join

        # set doctrsing
        doc: list[str] = (func.__doc__ or "").split("\n")
        example = (
            "\n"
            ".. code:: sql\n"
            "\n"
            f"    {'\n    '.join(self.sql.split('\n'))}"
            "\n"
        )
        doc.insert(1, example)
        func.__doc__ = "\n".join(doc)

        return func


@SqlLinker(
    ["enc_env_id", "enc_cmd", "enc_vid.vid_name AS enc_src_vid_name"],
    "t_enc_encode",
    ["JOIN t_vid_video AS enc_vid ON t_enc_encode.enc_src_vid_id = enc_vid.vid_id"],
)
def extract_enc_scenario(raw: dict[str]) -> str:
    """Return the unique string specific to the encoding scenario.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    Returns
    -------
    scenario : str
        Unique string specific to the encoding scenario.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_env_id" in raw, "Please correct the SQL query."
    assert "enc_cmd" in raw, "Please correct the SQL query."
    assert "enc_src_vid_name" in raw, "Please correct the SQL query."
    env_id, cmd, vid_name = raw["enc_env_id"], raw["enc_cmd"], raw["enc_src_vid_name"]
    assert isinstance(env_id, numbers.Integral), env_id.__class__.__name__
    assert isinstance(cmd, str), cmd.__class__.__name__
    assert isinstance(vid_name, str), vid_name.__class__.__name__
    return f"env {env_id}: {cmd.replace('src.mp4', vid_name)}"


@SqlLinker(
    ["enc_act.act_ps_dt AS enc_act_ps_dt", "enc_act.act_ps_core AS enc_act_ps_core"],
    "t_enc_encode",
    ["JOIN t_act_activity AS enc_act ON t_enc_encode.enc_act_id = enc_act.act_id"],
)
def extract_enc_cores(raw: dict[str]) -> float:
    """Return the average cumulative utilisation rate of logic cores during encoding.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    Returns
    -------
    enc_cores : int
        Average cumulative utilisation rate of logic cores during encoding.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_act_ps_dt" in raw, "Please correct the SQL query."
    assert "enc_act_ps_core" in raw, "Please correct the SQL query."
    act_ps_dt = binary_to_list(raw["enc_act_ps_dt"])
    act_ps_core = binary_to_tensor(raw["enc_act_ps_core"]).sum(axis=1)
    integral = (act_ps_core * act_ps_dt).sum()  # act_ps_core is already the average on each dt
    average = integral / act_ps_dt.sum()
    return float(average) / 100.0  # normalisation


@SqlLinker(
    ["enc_act.act_duration AS enc_act_duration"],
    "t_enc_encode",
    ["JOIN t_act_activity AS enc_act ON t_enc_encode.enc_act_id = enc_act.act_id"],
)
def extract_enc_duration(raw: dict[str]) -> float:
    """Return the video encoding time in seconds.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    Returns
    -------
    enc_duration : float
        Video encoding time in seconds.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_act_duration" in raw, "Please correct the SQL query."
    enc_duration = raw["enc_act_duration"]
    assert isinstance(enc_duration, numbers.Real), enc_duration.__class__.__name__
    assert enc_duration > 0.0, enc_duration.__class__.__name__
    return float(enc_duration)


@SqlLinker(["enc_effort"], "t_enc_encode", [])
def extract_enc_effort(raw: dict[str]) -> str:
    """Return the effort provided as a parameter to the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    Returns
    -------
    enc_effort : str
        Effort provided as a parameter to the encoder.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_effort" in raw, "Please correct the SQL query."
    enc_effort = raw["enc_effort"]
    assert isinstance(enc_effort, str), enc_effort.__class__.__name__
    return str(enc_effort)


@SqlLinker(["enc_threads"], "t_enc_encode", [])
def extract_enc_threads(raw: dict[str]) -> int:
    """Return the number of threads provided as a parameter to the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    Returns
    -------
    enc_threads : int
        Number of threads provided as a parameter to the encoder.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_threads" in raw, "Please correct the SQL query."
    enc_threads = raw["enc_threads"]
    assert isinstance(enc_threads, numbers.Integral), enc_threads.__class__.__name__
    assert enc_threads >= 1, enc_threads.__class__.__name__
    return int(enc_threads)


@SqlLinker(["enc_quality"], "t_enc_encode", [])
def extract_enc_quality(raw: dict[str]) -> float:
    """Return the quality level passed to the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    Returns
    -------
    quality : float
        Quality level passed to the encoder.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_quality" in raw, "Please correct the SQL query."
    enc_quality = raw["enc_quality"]
    assert isinstance(enc_quality, numbers.Real), enc_quality.__class__.__name__
    assert 0.0 <= enc_quality <= 1.0, enc_quality
    return float(enc_quality)


@SqlLinker(["enc_encoder"], "t_enc_encode", [])
def extract_enc_encoder(raw: dict[str]) -> str:
    """Return the name of the encoder.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    Returns
    -------
    encoder : str
        Name of the encoder.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_encoder" in raw, "Please correct the SQL query."
    enc_encoder = raw["enc_encoder"]
    assert isinstance(enc_encoder, str), enc_encoder.__class__.__name__
    return str(enc_encoder)


@SqlLinker(
    [
        "enc_act.act_wattmeter_dt AS enc_act_act_wattmeter_dt",
        "enc_act.act_wattmeter_power AS enc_act_wattmeter_power",
    ],
    "t_enc_encode",
    ["JOIN t_act_activity AS enc_act ON t_enc_encode.enc_act_id = enc_act.act_id"],
)
def extract_enc_wattmeter_energy(raw: dict[str]) -> float:
    """Return the total encoding energy consumption in Joules.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    Returns
    -------
    enc_power : float
        Total encoding energy consumption in Joules.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_act_act_wattmeter_dt" in raw, "Please correct the SQL query."
    assert "enc_act_wattmeter_power" in raw, "Please correct the SQL query."
    act_dt = binary_to_list(raw["enc_act_act_wattmeter_dt"])
    act_power = binary_to_list(raw["enc_act_wattmeter_power"])
    integral = 0.5 * ((act_power[:-1] + act_power[1:]) * act_dt).sum()  # trapez method
    return float(integral)


@SqlLinker(
    [
        "enc_act.act_wattmeter_dt AS enc_act_act_wattmeter_dt",
        "enc_act.act_wattmeter_power AS enc_act_wattmeter_power",
    ],
    "t_enc_encode",
    ["JOIN t_act_activity AS enc_act ON t_enc_encode.enc_act_id = enc_act.act_id"],
)
def extract_enc_wattmeter_power(raw: dict[str]) -> float:
    """Return the average encoding power consumption in Watts.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    Returns
    -------
    enc_power : float
        Average encoding power consumption in Watts.
    """
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_act_act_wattmeter_dt" in raw, "Please correct the SQL query."
    assert "enc_act_wattmeter_power" in raw, "Please correct the SQL query."
    act_dt = binary_to_list(raw["enc_act_act_wattmeter_dt"])
    act_power = binary_to_list(raw["enc_act_wattmeter_power"])
    integral = 0.5 * ((act_power[:-1] + act_power[1:]) * act_dt).sum()  # trapez method
    return float(integral / act_dt.sum())


@SqlLinker(["enc_width"], "t_enc_encode", [])
def extract_profile(raw: dict[str]) -> str:
    """Return the profile of the encoded video.

    The profile is determined based on the width of the video.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    Returns
    -------
    profile : str
        Profile of the encoded video.
    """
    from mendevi.cst.profiles import PROFILES
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_width" in raw, "Please correct the SQL query."
    enc_width = raw["enc_width"]
    assert isinstance(enc_width, numbers.Integral), enc_width.__class__.__name__
    dist_to_profile = {abs(v["resolution"][1]-enc_width): p for p, v in PROFILES.items()}
    return dist_to_profile[min(dist_to_profile)]


@SqlLinker(
    ["enc_vid.vid_name AS enc_src_vid_name"],
    "t_enc_encode",
    ["JOIN t_vid_video AS enc_vid ON t_enc_encode.enc_src_vid_id = enc_vid.vid_id"],
)
def extract_src_vid(raw: dict[str]) -> str:
    """Return the input video name.

    Parameters
    ----------
    raw : dict[str]
        The result line of select request.

    Returns
    -------
    vid_name : str
        Input video name.
    """
    from mendevi.cst.profiles import PROFILES
    assert isinstance(raw, dict), raw.__class__.__name__
    assert "enc_src_vid_name" in raw, "Please correct the SQL query."
    enc_src_vid_name = raw["enc_src_vid_name"]
    assert isinstance(enc_src_vid_name, str), enc_src_vid_name.__class__.__name__
    vid_name = re.sub(r"^reference_(\w+)_(?:sd|hd|fhd|uhd4k)\.\w+$", r"\1", enc_src_vid_name)
    return str(vid_name)
