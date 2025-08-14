#!/usr/bin/env python3

"""Fill the SQL database."""

import pathlib
import platform
import sqlite3
import time

import context_verbose as cv
import numpy as np

from mendevi.context import full_context
from mendevi.utils import Activity
from .create import ENV_UNIQUE, is_sqlite
from .serialize import list_to_binary, tensor_to_binary


def get_idle(duration: float=60.0) -> dict:
    """Measure the idle consumption.

    Parameters
    ----------
    duration : float, default=60
        The total duration of the measurement, bloking time in second.

    Returns
    -------
    measures : dict
        duration: float, the real measure duration
        ps_core: list[list[float]], tensor of detailed usage of each logical core in %
        ps_dt: list[float], the duration of each interval in seconds
        ps_ram: list[int], list of the sampled ram usage in bytes in each point
        rapl_dt: list[float], the duration of each interval in seconds
        rapl_power: list[float], the average power in watt in each interval
        start: float, absolute timestamp
        wattmeter_dt: list[float],  the duration of each interval in seconds
        wattmeter_power: list[float], the sampled power in watt in each point

    Examples
    --------
    >>> from mendevi.database.complete import get_idle
    >>> get_idle()
    >>>
    """
    assert isinstance(duration, float), duration.__class__.__name__
    assert duration > 0, duration.__class__.__name__

    with cv.Printer(f"Measure IDLE during {duration} seconds...") as printer:

        # measure IDLE
        with Activity() as activity:
            time.sleep(duration)

        # print
        printer.print(f"avg cpu usage: {activity['ps_core']:.1f} %")
        printer.print(f"avg ram usage: {1e-9*np.mean(activity['ps_ram']):.2g} Go")
        if "rapl_power" in activity:
            printer.print(f"avg rapl power: {activity['rapl_power']:.2g} W")
        if "wattmeter_power" in activity:
            printer.print(f"avg wattmeter power: {activity['wattmeter_power']:.2g} W")

    return activity


def add_environement(database: sqlite3.Cursor | str | bytes | pathlib.Path) -> int:
    """Complete the environment table with the current environment.

    Parameters
    ----------
    database : pathlike
        The path of the existing database to be updated.

    Returns
    -------
    id : int
        The primary key of the freshly updated environment table.

    Examples
    --------
    >>> import os, tempfile
    >>> from mendevi.database.complete import add_environement
    >>> from mendevi.database.create import create_database
    >>> create_database(database := tempfile.mktemp(suffix=".sqlite"))
    >>> add_environement(database)
    1
    >>> os.remove(database)
    >>>
    """
    # open file
    if not isinstance(database, sqlite3.Cursor):
        database = pathlib.Path(database).expanduser().resolve()
        assert is_sqlite(database), database
        with sqlite3.connect(database) as sql_database:
            # sql_database.execute("PRAGMA journal_mode=WAL")
            cursor = sql_database.cursor()
            key = add_environement(cursor)
            cursor.close()
            return key

    # try to set the context
    environement = full_context()
    environement = {f"env_{k}": v for k, v in environement.items()}
    keys = list(environement)  # to keep order
    try:
        (env_id,) = database.execute(
            (
                f"INSERT INTO t_env_environement ({', '.join(keys)}) "
                f"VALUES ({', '.join('?'*len(keys))}) RETURNING env_id"
            ),
            [environement[k] for k in keys],
        ).fetchone()
    except sqlite3.IntegrityError:
        (env_id,) = database.execute(
            (
                "SELECT env_id FROM t_env_environement "
                f"WHERE {' AND '.join(f'{k}=?' for k in ENV_UNIQUE)}"
            ),
            [environement[k] for k in ENV_UNIQUE],
        ).fetchone()
        return env_id

    # get idle
    idle = get_idle()
    idle = {
        "act_duration": idle["duration"],
        "act_ps_core": tensor_to_binary(idle["ps_cores"]),
        "act_ps_dt": list_to_binary(idle["ps_dt"]),
        "act_ps_ram": list_to_binary(idle["ps_ram"]),
        "act_rapl_dt": list_to_binary(idle.get("rapl_dt", None)),
        "act_rapl_power": list_to_binary(idle.get("rapl_powers", None)),
        "act_start": idle["start"],
        "act_wattmeter_dt": list_to_binary(idle.get("wattmeter_dt", None)),
        "act_wattmeter_power": list_to_binary(idle.get("wattmeter_powers", None)),
    }
    keys = list(idle)
    (act_id,) = database.execute(
        (
            f"INSERT INTO t_act_activity ({', '.join(keys)}) "
            f"VALUES ({', '.join('?'*len(keys))}) RETURNING act_id"
        ),
        [idle[k] for k in keys],
    ).fetchone()
    database.execute(
        (
            f"UPDATE t_env_environement SET env_act_id={act_id} "
            f"WHERE {' AND '.join(f'{k}=?' for k in ENV_UNIQUE)}"
        ),
        [environement[k] for k in ENV_UNIQUE],
    )
    return env_id
