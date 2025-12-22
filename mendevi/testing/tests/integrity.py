"""Benchmark."""

import pathlib
import sqlite3
import tempfile
import time

import pytest

from mendevi.database.create import create_database


def test_unicity_activity_from_env() -> None:
    """Ensure it raise and exception."""
    create_database(database := tempfile.mktemp(suffix=".sqlite"))

    # create 4 activities and a video
    with sqlite3.connect(database) as conn:
        for _ in range(4):
            conn.execute(
                "INSERT INTO t_act_activity (act_start, act_duration) VALUES (?, ?)",
                (time.time(), 1.0),
            )
        conn.execute(
            "INSERT INTO t_vid_video (vid_id) VALUES (?)",
            ((0).to_bytes(16),),
        )

    # insert encode and decode
    with sqlite3.connect(database) as conn:
        conn.execute(
            "INSERT INTO t_enc_encode (enc_dst_vid_id, enc_env_id) VALUES (?, ?)",
            ((0).to_bytes(16), 0),
        )
        conn.execute(
            "INSERT INTO t_dec_decode (dec_vid_id, dec_env_id) VALUES (?, ?)",
            ((0).to_bytes(16), 1),
        )

    # insert environment OK
    with sqlite3.connect(database) as conn:
        conn.execute(
            """
            INSERT INTO t_env_environment
            (env_ffmpeg_version, env_hostname, env_logical_cores, env_ram, env_idle_act_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("ffmpeg 0.0.0", "my_name", 8, 1024, 2),
        )

    # insert environnement FAIL
    with sqlite3.connect(database) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO t_env_environment
            (env_ffmpeg_version, env_hostname, env_logical_cores, env_ram, env_idle_act_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("ffmpeg 0.0.1", "my_name", 8, 1024, 2),
        )

    # insert environment OK
    with sqlite3.connect(database) as conn:
        conn.execute(
            """
            INSERT INTO t_env_environment
            (env_ffmpeg_version, env_hostname, env_logical_cores, env_ram, env_idle_act_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("ffmpeg 0.0.2", "my_name", 8, 1024, 3),
        )

    # insert environment OK null env_idle_act_id
    with sqlite3.connect(database) as conn:
        conn.execute(
            """
            INSERT INTO t_env_environment
            (env_ffmpeg_version, env_hostname, env_logical_cores, env_ram)
            VALUES (?, ?, ?, ?)
            """,
            ("ffmpeg 0.0.3", "my_name", 8, 1024),
        )

    # insert environment OK null env_idle_act_id second time
    with sqlite3.connect(database) as conn:
        conn.execute(
            """
            INSERT INTO t_env_environment
            (env_ffmpeg_version, env_hostname, env_logical_cores, env_ram)
            VALUES (?, ?, ?, ?)
            """,
            ("ffmpeg 0.0.4", "my_name", 8, 1024),
        )

    # update environment FAIL
    with sqlite3.connect(database) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            UPDATE t_env_environment SET env_idle_act_id=3
            WHERE env_ffmpeg_version=? AND env_hostname=? AND env_logical_cores=? AND env_ram=?
            """,
            ("ffmpeg 0.0.3", "my_name", 8, 1024),
        )

    pathlib.Path(database).unlink()
