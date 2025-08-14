#!/usr/bin/env python3

"""Benchmark."""

import os
import sqlite3
import tempfile
import time

import pytest

from mendevi.database.create import create_database


def test_unicity_activity_from_env():
    """Ensure it raise and exception."""
    create_database(database := tempfile.mktemp(suffix=".sqlite"))

    # create 4 activities and a video
    with sqlite3.connect(database) as sql_database:
        for _ in range(4):
            sql_database.execute(
                "INSERT INTO t_act_activity (act_start, act_duration) VALUES (?, ?)",
                (time.time(), 1.0)
            )
        sql_database.execute(
            "INSERT INTO t_vid_video (vid_id) VALUES (?)",
            ((0).to_bytes(16),)
        )

    # insert encode and decode
    with sqlite3.connect(database) as sql_database:
        sql_database.execute(
            "INSERT INTO t_enc_encode (enc_vid_id, enc_env_id) VALUES (?, ?)",
            ((0).to_bytes(16), 0)
        )
        sql_database.execute(
            "INSERT INTO t_dec_decode (dec_vid_id, dec_env_id) VALUES (?, ?)",
            ((0).to_bytes(16), 1)
        )

    # insert environement OK
    with sqlite3.connect(database) as sql_database:
        sql_database.execute("""INSERT INTO t_env_environement
            (env_ffmpeg_version, env_hostname, env_logical_cores, env_ram, env_act_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("ffmpeg 0.0.0", "my_name", 8, 1024, 2)
        )

    # insert environnement FAIL
    with sqlite3.connect(database) as sql_database, pytest.raises(sqlite3.IntegrityError):
        sql_database.execute("""INSERT INTO t_env_environement
            (env_ffmpeg_version, env_hostname, env_logical_cores, env_ram, env_act_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("ffmpeg 0.0.1", "my_name", 8, 1024, 2)
        )

    # insert environement OK
    with sqlite3.connect(database) as sql_database:
        sql_database.execute("""INSERT INTO t_env_environement
            (env_ffmpeg_version, env_hostname, env_logical_cores, env_ram, env_act_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("ffmpeg 0.0.2", "my_name", 8, 1024, 3)
        )

    # insert environement OK null env_act_id
    with sqlite3.connect(database) as sql_database:
        sql_database.execute("""INSERT INTO t_env_environement
            (env_ffmpeg_version, env_hostname, env_logical_cores, env_ram)
            VALUES (?, ?, ?, ?)
            """,
            ("ffmpeg 0.0.3", "my_name", 8, 1024)
        )

    # insert environement OK null env_act_id second time
    with sqlite3.connect(database) as sql_database:
        sql_database.execute("""INSERT INTO t_env_environement
            (env_ffmpeg_version, env_hostname, env_logical_cores, env_ram)
            VALUES (?, ?, ?, ?)
            """,
            ("ffmpeg 0.0.4", "my_name", 8, 1024)
        )

    # update environement FAIL
    with sqlite3.connect(database) as sql_database, pytest.raises(sqlite3.IntegrityError):
        sql_database.execute("""UPDATE t_env_environement SET env_act_id=3
            WHERE env_ffmpeg_version=? AND env_hostname=? AND env_logical_cores=? AND env_ram=?
            """,
            ("ffmpeg 0.0.3", "my_name", 8, 1024)
        )

    os.remove(database)

