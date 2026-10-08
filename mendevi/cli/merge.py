# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Merge databases.

Remove fields with empty wattmeter value
========================================

.. code:: sql

    -- 1) Metrics where the distorted video is caused by encoding that needs to be removed
    DELETE FROM t_met_metric
    WHERE met_dis_vid_id IN (
        SELECT enc_dst_vid_id FROM t_enc_encode
        WHERE enc_act_id IN (
            SELECT act_id FROM t_act_activity
            WHERE act_wattmeter_dt IS NULL OR act_wattmeter_power IS NULL
        )
    );

    -- 2) Activity-related encodings to be deleted
    DELETE FROM t_enc_encode
    WHERE enc_act_id IN (
        SELECT act_id FROM t_act_activity
        WHERE act_wattmeter_dt IS NULL OR act_wattmeter_power IS NULL
    );

    -- 3) Orphaned videos (encoding output deleted, no longer referenced anywhere)
    DELETE FROM t_vid_video
    WHERE vid_id NOT IN (SELECT enc_src_vid_id FROM t_enc_encode)
      AND vid_id NOT IN (SELECT enc_dst_vid_id FROM t_enc_encode)
      AND vid_id NOT IN (SELECT dec_vid_id     FROM t_dec_decode)
      AND vid_id NOT IN (SELECT met_ref_vid_id FROM t_met_metric)
      AND vid_id NOT IN (SELECT met_dis_vid_id FROM t_met_metric);

    -- 4) Decoding related to activities to be discontinued
    DELETE FROM t_dec_decode
    WHERE dec_act_id IN (
        SELECT act_id FROM t_act_activity
        WHERE act_wattmeter_dt IS NULL OR act_wattmeter_power IS NULL
    );

    -- 5) Environments where the IDLE activity has been removed - NULL (the environment is keeped)
    UPDATE t_env_environment
    SET env_idle_act_id = NULL
    WHERE env_idle_act_id IN (
        SELECT act_id FROM t_act_activity
        WHERE act_wattmeter_dt IS NULL OR act_wattmeter_power IS NULL
    );

    -- 6) Finally: remove the activities themselves
    DELETE FROM t_act_activity
    WHERE act_wattmeter_dt IS NULL OR act_wattmeter_power IS NULL;

"""

import pathlib
import sqlite3

import click
from context_verbose import Printer

from mendevi.database.create import ENV_UNIQUE, create_database
from mendevi.download.decapsulation import retrive_file

from .parse import parse_videos_database


def _insert_update(
    cursor: sqlite3.Cursor, row: sqlite3.Row | dict, tab: str, keys: tuple[str],
) -> dict[str]:
    """Set or update the tab of the cursor with the new line."""
    line: dict[str] = {k: v for k, v in dict(row).items() if v is not None}
    ids = tuple(line.pop(k) for k in keys)
    line_keys = tuple(line)  # frozen the order
    line_values = tuple(line[k] for k in line_keys)
    try:
        out = cursor.execute(
            (
                f"INSERT INTO {tab} ({', '.join(keys + line_keys)}) "
                f"VALUES ({', '.join('?'*len(keys + line_keys))}) "
                "RETURNING *"
            ),
            ids + line_values,
        ).fetchone()
    except sqlite3.IntegrityError:  # if exists
        cursor.execute(
            (
                f"UPDATE {tab} SET {', '.join(f'{k}=?' for k in line_keys)} "
                f"WHERE {' AND '.join(f'{k}=?' for k in keys)}"
            ),
            line_values + ids,
        )
        out = cursor.execute(
            f"SELECT * FROM {tab} WHERE {' AND '.join(f'{k}=?' for k in keys)}",
            ids,
        ).fetchone()
    return dict(out)


def _parse(databases: tuple[str], **kwargs: dict) -> tuple[list[pathlib.Path], pathlib.Path]:
    """Help for main."""
    with Printer("Parse configuration...") as prt:
        assert isinstance(databases, (tuple, list, set, frozenset)), databases.__class__.__name__
        all_databases: list[pathlib.Path] = []
        for i, database_ in enumerate(databases):
            database = retrive_file(database_)
            _, database = parse_videos_database(prt, (), database, _quiet=True)
            all_databases.append(database)
            prt.print(f"database {i+1:>2}: {database}")

        if (dst := kwargs.get("output")) is None:
            dst = pathlib.Path(f"merge_{'_'.join(d.stem for d in all_databases)}.db")
        else:
            dst = pathlib.Path(dst).expanduser()
            if dst.is_dir():
                dst = dst / f"merge_{'_'.join(d.stem for d in all_databases)}.db"
        create_database(dst)
        prt.print(f"destination: {dst} (just created)")
    return all_databases, dst


@click.command()
@click.argument("databases", type=click.Path(), nargs=-1)
@click.option("-o", "--output", type=click.Path(), help="The output sql database path.")
def main(databases: tuple[str], **kwargs: dict) -> None:
    """Merge several SQL databases together.

    \b
    You can test if the database is corrupted with:
    ``sqlite3 mendevi.db "PRAGMA integrity_check;"``.
    If is raises "ok", it means the database is corrupted.
    You can fix it with ``sqlite3 mendevi.db ".recover" | sqlite3 mendevi_recovered.db``.

    \b
    Parameters
    ----------
    databases : list[pathlike]
        All databases to be merged.
    **kwargs: dict
        Please refer to the detailed arguments below.
    output : pathlike, optional
        The destination sql database path.
        By default, the file is created in the same folder than the SQL database.
        The new name starts with the prefix "merge_".

    """
    all_databases, dst = _parse(databases, **kwargs)
    with sqlite3.connect(dst) as conn_dst:
        conn_dst.row_factory = sqlite3.Row
        cursor_dst = conn_dst.cursor()
        for database in all_databases:
            with (
                Printer(f"Add {database.name} into {dst.name}...", color="cyan") as prt,
                sqlite3.connect(f"file:{database}?mode=ro&immutable=1", uri=True) as conn_src,
            ):
                conn_src.row_factory = sqlite3.Row
                cursor_src = conn_src.cursor()

                # t_vid_video
                prt.print("table 't_vid_video'")
                for row_ in cursor_src.execute("SELECT * FROM t_vid_video"):
                    _insert_update(cursor_dst, row_, "t_vid_video", ("vid_id",))

                # t_met_metric
                prt.print("table 't_met_metric'")
                for row_ in cursor_src.execute("SELECT * FROM t_met_metric"):
                    row = dict(row_)
                    del row["met_id"]
                    _insert_update(
                        cursor_dst, row, "t_met_metric", ("met_ref_vid_id", "met_dis_vid_id"),
                    )

                # t_act_activity
                prt.print("table 't_act_activity'")
                act_old_to_new: dict[int, int] = {}
                for row_ in cursor_src.execute("SELECT * FROM t_act_activity"):
                    row = dict(row_)
                    old = row.pop("act_id")

                # t_env_environment
                prt.print("table 't_env_environment'")
                env_old_to_new: dict[int, int] = {}
                env_unique = tuple(ENV_UNIQUE)
                for row_ in cursor_src.execute("SELECT * FROM t_env_environment"):
                    row = dict(row_)
                    row["env_idle_act_id"] = act_old_to_new[row["env_idle_act_id"]]
                    old = row.pop("env_id")
                    row["env_libvvenc_version"] = row.pop(
                        "env_vvc_version",  # retrocompatibility with version <= 1.3.7
                    )
                    new = _insert_update(cursor_dst, row, "t_env_environment", env_unique)["env_id"]
                    env_old_to_new[old] = new

                # t_enc_encode
                prt.print("table 't_enc_encode'")
                for row_ in cursor_src.execute("SELECT * FROM t_enc_encode"):
                    row = dict(row_)
                    del row["enc_id"]
                    row["enc_env_id"] = env_old_to_new[row["enc_env_id"]]
                    row["enc_act_id"] = act_old_to_new[row["enc_act_id"]]
                    row["enc_mode"] = {"vbr": "crf"}.get(
                        row["enc_mode"], row["enc_mode"],
                    )  # retrocompatibility with version <= 1.3.6
                    _insert_update(cursor_dst, row, "t_enc_encode", ())

                # t_dec_decode
                prt.print("table 't_dec_decode'")
                for row_ in cursor_src.execute("SELECT * FROM t_dec_decode"):
                    row = dict(row_)
                    del row["dec_id"]
                    row["dec_env_id"] = env_old_to_new[row["dec_env_id"]]
                    row["dec_act_id"] = act_old_to_new[row["dec_act_id"]]
                    _insert_update(cursor_dst, row, "t_dec_decode", ())
