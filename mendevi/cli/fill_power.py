"""Attempt to complete the empty fields 'act_wattmeter*'."""

import datetime
import logging
import pathlib
import sqlite3
import time

import click
import torch
import tqdm
from context_verbose import Printer
from flufl.lock import Lock

from mendevi.database.serialize import list_to_binary
from mendevi.measures.g5kpower import g5kpower

from .parse import parse_videos_database

INTERVAL = 300  # time in seconds between 2 database flush


def get_power(hostname: str, start: float, duration: float, **kwargs: dict) -> tuple[bytes, bytes]:
    """Exctract the wattmeters data for that specific activity."""
    wattmeter_ts, wattmeter_power = g5kpower(
        hostname, start, duration, login=kwargs.get("login"), password=kwargs.get("password"),
    )
    wattmeter_ts = torch.asarray(wattmeter_ts, dtype=torch.float64)
    wattmeter_dt = (wattmeter_ts[1:] - wattmeter_ts[:-1]).tolist()
    return list_to_binary(wattmeter_dt), list_to_binary(wattmeter_power)


@click.command()
@click.argument("database", type=click.Path())
@click.option(
    "-l", "--login",
    type=str,
    help="The grid'5000 login to request the api.",
)
@click.option(
    "-p", "--password",
    type=str,
    help="The grid'5000 password to request the api.",
)
def main(database: str, **kwargs: dict) -> None:
    """Injects or updates power data into the database.

    \b
    Parameters
    ----------
    database : pathlike
        The source SQL database to be filled.
    **kwargs: dict
        Please refer to the detailed arguments below.
    login, password : str, optional
        The grid'5000 login and password to acces the api from the outside.

    """
    # parse args
    with Printer("Parse configuration...") as prt:
        _, database = parse_videos_database(prt, (), database)

    # get missing fields
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as conn:
        fields = conn.execute(  # UNION ALL faster than UNION
            """
            SELECT act_id, act_start, act_duration, env_hostname
            FROM t_env_environment
            JOIN t_act_activity ON t_act_activity.act_id = t_env_environment.env_idle_act_id
            WHERE act_wattmeter_dt IS NULL or act_wattmeter_power IS NULL

            UNION ALL

            SELECT act_id, act_start, act_duration, env_hostname
            FROM t_enc_encode
            JOIN t_act_activity ON t_act_activity.act_id = t_enc_encode.enc_act_id
            JOIN t_env_environment ON t_env_environment.env_id = t_enc_encode.enc_env_id
            WHERE act_wattmeter_dt IS NULL or act_wattmeter_power IS NULL

            UNION ALL

            SELECT act_id, act_start, act_duration, env_hostname
            FROM t_dec_decode
            JOIN t_act_activity ON t_act_activity.act_id = t_dec_decode.dec_act_id
            JOIN t_env_environment ON t_env_environment.env_id = t_dec_decode.dec_env_id
            WHERE act_wattmeter_dt IS NULL or act_wattmeter_power IS NULL
            """,
        ).fetchall()  # no duplication issue thanks creation process

    def _flush_buff(buff: list, database: pathlib.Path) -> None:
        """Add the fields into the database."""
        with (
            Lock(str(database.with_suffix(".lock")), lifetime=datetime.timedelta(seconds=600)),
            sqlite3.connect(database) as conn,
        ):
            cursor = conn.cursor()
            for act_id, wattmeter_dt, wattmeter_power in buff:
                cursor.execute(
                    """
                    UPDATE t_act_activity SET act_wattmeter_dt=?, act_wattmeter_power=?
                    WHERE act_id=?
                    """,
                    (wattmeter_dt, wattmeter_power, act_id),
                )

    # fill missing data
    timestamp, buff = time.time(), []
    for act_id, start, duration, hostname in tqdm.tqdm(
        fields,
        dynamic_ncols=True,
        leave=True,
        smoothing=1e-8,
        unit="measures",
    ):
        try:
            buff.append([act_id, *get_power(hostname, start, duration, **kwargs)])
        except ValueError:
            logging.getLogger(__name__).exception("skip act_id=%s", act_id)
            continue
        if time.time() - timestamp >= INTERVAL:
            _flush_buff(buff, database)
            timestamp, buff = time.time(), []
    _flush_buff(buff, database)
