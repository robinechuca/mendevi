"""Extract simple constants in order to 'normalize' the values."""

import datetime
import sqlite3
import pathlib

from flufl.lock import Lock

from .create import is_sqlite
from .serialize import binary_to_list


def p_static_p_core(database: sqlite3.Cursor | str | bytes | pathlib.Path) -> dict[str, tuple]:
    """Estimate for each hostname, the model P = P_static + c * P_core.

    Parameters
    ----------
    database : pathlike
        The path of the existing database to be updated.

    Returns
    -------
    cst : dict
        To each hostname, associate the estimation of (p_static, p_core).

    Examples
    --------
    >>> from mendevi.database.normalize import p_static_p_core
    >>> p_static_p_core("/data/dataset/merge.db")
    >>>
    """
    # open file
    if not isinstance(database, sqlite3.Cursor):
        database = pathlib.Path(database).expanduser()
        assert is_sqlite(database), database
        with (
            Lock(str(database.with_suffix(".lock")), lifetime=datetime.timedelta(seconds=1800)),
            sqlite3.connect(database) as conn,
        ):
            cursor = conn.cursor()
            estimation = p_static_p_core(cursor)
            cursor.close()
            return estimation

    # perform request
    for data in database.execute(
        """
        SELECT act_rapl_dt, act_rapl_power, act_wattmeter_dt, act_wattmeter_power
        """
    ):
        print(data)
