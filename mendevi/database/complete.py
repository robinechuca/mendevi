"""Fill the SQL database."""

import datetime
import pathlib
import sqlite3
import time

import context_verbose as cv
import numpy as np
import orjson
from flufl.lock import Lock

from mendevi.measures import Activity
from mendevi.measures.context import full_context

from .create import ENV_UNIQUE, is_sqlite
from .serialize import list_to_binary, tensor_to_binary


def get_idle(duration: float = 60.0) -> dict:
    """Measure the idle consumption.

    Parameters
    ----------
    duration : float, default=60
        The total duration of the measurement, bloking time in second.

    Returns
    -------
    measures : dict
        Same as :py:class:`mendevi.measures.Activity`.

    Examples
    --------
    >>> from mendevi.database.complete import get_idle
    >>> idle = get_idle(duration=1.0)  # doctest: +ELLIPSIS
    Measure IDLE during 1.0 seconds...
    █ avg cpu usage: ... %
    █ avg ram usage: ... Go
    █ avg rapl power: ... W
    >>>

    """
    assert isinstance(duration, float), duration.__class__.__name__
    assert duration > 0.0, duration.__class__.__name__

    with cv.Printer(f"Measure IDLE during {duration} seconds...") as printer:

        # measure IDLE
        with Activity() as activity:
            time.sleep(duration)

        # print
        printer.print(f"avg cpu usage: {activity['ps_core']:.1f} %")
        printer.print(f"avg ram usage: {1e-9*np.mean(activity['ps_ram']):.2g} Go")
        if "rapl_power" in activity:
            printer.print(f"avg rapl power: {activity['rapl_power']:.2g} W")
        if "gpu_power" in activity:
            printer.print(f"avg GPU power: {activity['gpu_power']:.2g} W")
        if "wattmeter_power" in activity:
            printer.print(f"avg wattmeter power: {activity['wattmeter_power']:.2g} W")

    return activity


def add_environment(database: sqlite3.Cursor | str | bytes | pathlib.Path) -> int:
    """Complete the environment table with the current environment.

    Parameters
    ----------
    database : pathlike
        The path of the existing database to be updated.

    Returns
    -------
    id : int
        The primary key of the freshly updated environment table.

    """
    # open file
    if not isinstance(database, sqlite3.Cursor):
        database = pathlib.Path(database).expanduser()
        assert is_sqlite(database), database
        with (
            Lock(str(database.with_name(".dblock")), lifetime=datetime.timedelta(seconds=1800)),
            sqlite3.connect(database) as conn,
        ):
            cursor = conn.cursor()
            key = add_environment(cursor)
            cursor.close()
            return key

    # try to set the context
    environment = full_context()
    environment = {f"env_{k}": v for k, v in environment.items()}
    keys = list(environment)  # to keep order
    try:
        (env_id,) = database.execute(
            (
                f"INSERT INTO t_env_environment ({', '.join(keys)}) "
                f"VALUES ({', '.join('?'*len(keys))}) RETURNING env_id"
            ),
            [environment[k] for k in keys],
        ).fetchone()
    except sqlite3.IntegrityError:
        (env_id,) = database.execute(
            (
                "SELECT env_id FROM t_env_environment "
                f"WHERE {' AND '.join(f'{k}=?' for k in ENV_UNIQUE)}"
            ),
            [environment[k] for k in ENV_UNIQUE],
        ).fetchone()
        return env_id

    # get idle
    idle = get_idle()
    idle = {
        "act_duration": idle["duration"],
        "act_ps_core": tensor_to_binary(idle["ps_cores"]),
        "act_ps_dt": list_to_binary(idle["ps_dt"]),
        "act_ps_temp": orjson.dumps(
            idle["ps_temp"], option=orjson.OPT_INDENT_2|orjson.OPT_SORT_KEYS,
        ),
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
            f"UPDATE t_env_environment SET env_idle_act_id={act_id} "
            f"WHERE {' AND '.join(f'{k}=?' for k in ENV_UNIQUE)}"
        ),
        [environment[k] for k in ENV_UNIQUE],
    )
    return env_id
