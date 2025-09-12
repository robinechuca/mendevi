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
        join_str = "\n".join(re.sub(" ON ", "\n    ON ", j) for j in self.join)
        sql = f"{select_str}\n{table_str}\n{join_str}"
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
