"""Merge databases."""

import pathlib
import sqlite3

import click
from context_verbose import Printer

from mendevi.database.create import ENV_UNIQUE, create_database

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


@click.command()
@click.argument("databases", type=click.Path(), nargs=-1)
def main(databases: tuple[str]) -> None:
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

    """
    with Printer("Parse configuration...") as prt:
        assert isinstance(databases, (tuple, list, set, frozenset)), databases.__class__.__name__
        all_databases: list[pathlib.Path] = []
        for i, database_ in enumerate(databases):
            _, database = parse_videos_database(prt, (), database_, _quiet=True)
            all_databases.append(database)
            prt.print(f"database {i+1:>2}: {database}")
        dst = pathlib.Path(f"merge_{'_'.join(d.stem for d in all_databases)}.db")
        create_database(dst)
        prt.print(f"destination: {dst} (just created)")

    with sqlite3.connect(dst) as conn_dst:
        conn_dst.row_factory = sqlite3.Row
        cursor_dst = conn_dst.cursor()
        for database in all_databases:
            with (
                Printer(f"Add {database.name} into {dst.name}...", color="cyan") as prt,
                sqlite3.connect(f"file:{database}?mode=ro", uri=True) as conn_src,
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
                    new = _insert_update(cursor_dst, row, "t_act_activity", ())["act_id"]
                    act_old_to_new[old] = new

                # t_env_environment
                prt.print("table 't_env_environment'")
                env_old_to_new: dict[int, int] = {}
                env_unique = tuple(ENV_UNIQUE)
                for row_ in cursor_src.execute("SELECT * FROM t_env_environment"):
                    row = dict(row_)
                    row["env_idle_act_id"] = act_old_to_new[row["env_idle_act_id"]]
                    old = row.pop("env_id")
                    new = _insert_update(cursor_dst, row, "t_env_environment", env_unique)["env_id"]
                    env_old_to_new[old] = new

                # t_enc_encode
                prt.print("table 't_enc_encode'")
                for row_ in cursor_src.execute("SELECT * FROM t_enc_encode"):
                    row = dict(row_)
                    del row["enc_id"]
                    if "enc_vbr" in row:  # retrocompatibility with version <= 1.2.0
                        row["enc_mode"] = "vbr" if row.pop("enc_vbr") else "cbr"
                    row["enc_env_id"] = env_old_to_new[row["enc_env_id"]]
                    row["enc_act_id"] = act_old_to_new[row["enc_act_id"]]
                    _insert_update(cursor_dst, row, "t_enc_encode", ())

                # t_dec_decode
                prt.print("table 't_dec_decode'")
                for row_ in cursor_src.execute("SELECT * FROM t_dec_decode"):
                    row = dict(row_)
                    del row["dec_id"]
                    row["dec_env_id"] = env_old_to_new[row["dec_env_id"]]
                    row["dec_act_id"] = act_old_to_new[row["dec_act_id"]]
                    _insert_update(cursor_dst, row, "t_dec_decode", ())
