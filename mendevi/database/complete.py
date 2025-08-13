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
from .create import is_sqlite


def idle(duration: float=60.0) -> dict:
    """Measure the idle consuption.

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
    >>> from mendevi.database.complete import idle
    >>> idle()
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

    # select and rename fields
    return {
        "duration": activity["duration"],
        "ps_core": activity["ps_cores"],
        "ps_dt": activity["ps_dt"],
        "ps_ram": activity["ps_ram"],
        "rapl_dt": activity.get("rapl_dt", None),
        "rapl_power": activity.get("rapl_powers", None),
        "start": activity["start"],
        "wattmeter_dt": activity.get("wattmeter_dt", None),
        "wattmeter_power": activity.get("wattmeter_powers", None),
    }


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

    # get context
    context = full_context()

    # search if context is in database
    keys = list(context)
    (env_id,) = database.execute(
        f"INSERT INTO environement ({', '.join(keys)}) VALUES ({', '.join('?'*len(keys))}) RETURNING id",
        [context[k] for k in keys],
    ).fetchone()

    return env_id

