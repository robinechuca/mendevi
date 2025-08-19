#!/usr/bin/env python3

"""Initialize the SQL database."""

import pathlib
import sqlite3


ENV_UNIQUE = ["env_ffmpeg_version", "env_hostname", "env_logical_cores", "env_ram"]


def create_database(filename: str | bytes | pathlib.Path):
    """Create a new SQL database to store all video informations.

    Parameters
    ----------
    filename : pathlike
        The path of the new database to be created.

    Examples
    --------
    >>> import os, tempfile
    >>> from mendevi.database.create import create_database
    >>> create_database(database := tempfile.mktemp(suffix=".sqlite"))
    >>> os.remove(database)
    >>>
    """
    filename = pathlib.Path(filename).expanduser().resolve()
    assert not filename.exists(), f"the database has to be new, {filename} exists"

    with sqlite3.connect(filename) as sql_database:
        cursor = sql_database.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS t_act_activity (
            act_id INTEGER PRIMARY KEY AUTOINCREMENT,

            /* MEASURES */
            act_start TIMESTAMP NOT NULL,  -- absolute start timestamp
            act_duration FLOAT NOT NULL CHECK(act_duration > 0.0),  -- full encoding time in seconds
            act_rapl_dt LONGBLOB,  -- list of the duration of each interval in seconds
            act_rapl_power LONGBLOB,  -- list of the average power in watt in each interval
            act_wattmeter_dt LONGBLOB,  -- list of the duration of each interval in seconds
            act_wattmeter_power LONGBLOB,  -- list of the sampled power in watt in each point
            act_ps_dt LONGBLOB,  -- list of the duration of each interval in seconds
            act_ps_core LONGBLOB,  -- tensor of detailed usage of each logical core in %
            act_ps_ram LONGBLOB  -- list of the sampled ram usage in bytes in each point
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS t_vid_video (
            vid_id BINARY(128) PRIMARY KEY,  -- md5 hash of the video

            /* VIDEO CONTENT */
            vid_codec TINYTEXT,  -- the codec name
            vid_duration FLOAT CHECK(vid_duration > 0.0),  -- video duration in second
            vid_eotf TINYTEXT,  -- name of the electro optical transfer function
            vid_fps FLOAT CHECK(vid_fps > 0.0),  -- theorical framerate of the video
            vid_frames LONGBLOB,  -- serialized version of the metadata of all frames
            vid_gamut TINYTEXT,  -- name of the color space
            vid_height SMALLINT CHECK(vid_height > 0),  -- display height
            vid_size BIGINT CHECK(vid_width >= 0),  -- file size in bytes
            vid_subsampling TINYTEXT CHECK(vid_subsampling IN ('444', '422', '420')),  -- yuv pixel subsampling
            vid_width SMALLINT CHECK(vid_width > 0),  -- display width
            vid_bit_depth SMALLINT CHECK(vid_bit_depth IN (8, 10, 12)),  -- bit per sample

            /* METRICS */
            vid_lpips_alex LONGBLOB,  -- list lpips with alex for each frame
            vid_lpips_vgg LONGBLOB,  -- list lpips with vgg for each frame
            vid_psnr LONGBLOB,  -- list of the psnr (6, 1, 1) metric for each frame
            vid_ssim LONGBLOB,  -- list of the ssim (6, 1, 1) metric for each frame, gauss win 11x11
            vid_uvq LONGBLOB  -- list of the google uvq metric for each second of video
        )""")
        cursor.execute(f"""CREATE TABLE IF NOT EXISTS t_env_environement (
            env_id INTEGER PRIMARY KEY AUTOINCREMENT,

            /* CONTEXT DETAILS */
            env_ffmpeg_version MEDIUMTEXT NOT NULL,
            env_hostname TINYTEXT NOT NULL,
            env_kernel_version TINYTEXT,
            env_libsvtav1_version MEDIUMTEXT,
            env_libvpx_vp9_version MEDIUMTEXT,
            env_libx265_version MEDIUMTEXT,
            env_logical_cores INTEGER NOT NULL CHECK(env_logical_cores > 0),
            env_lshw LONGTEXT,
            env_physical_cores INTEGER,
            env_pip_freeze MEDIUMTEXT,
            env_processor TINYTEXT,
            env_python_compiler TINYTEXT,
            env_python_version TINYTEXT,
            env_ram INTEGER NOT NULL CHECK(env_ram > 0),
            env_swap INTEGER,
            env_system_version MEDIUMTEXT,
            env_vvc_version MEDIUMTEXT,

            /* IDLE MEASURES */
            env_act_id INTEGER REFERENCES t_act_activity(act_id),  -- link to activity table

            /* CONSTRAINTS */
            UNIQUE({", ".join(ENV_UNIQUE)}) ON CONFLICT FAIL
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS t_dec_decode (
            dec_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dec_vid_id BINARY(128) NOT NULL REFERENCES t_vid_video(vid_id) ON DELETE CASCADE,  -- link to video table
            dec_env_id INTEGER NOT NULL REFERENCES t_env_environement(env_id) ON DELETE CASCADE,  -- link to environement table
            dec_act_id INTEGER REFERENCES t_act_activity(act_id)  -- link to activity table
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS t_enc_encode (
            enc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            enc_vid_id BINARY(128) NOT NULL REFERENCES t_vid_video(vid_id) ON DELETE CASCADE,  -- link to video table
            enc_env_id INTEGER NOT NULL REFERENCES t_env_environement(env_id) ON DELETE CASCADE,  -- link to environement table
            enc_act_id INTEGER REFERENCES t_act_activity(act_id),  -- link to activity table

            /* TASK DESCRIPTION */
            enc_cmd TEXT,  -- exact ffmpeg command used
            enc_effort TINYTEXT CHECK(enc_effort IN ('fast', 'medium', 'slow')),  -- equivalent preset used for encoding
            enc_encoder TINYTEXT CHECK(enc_encoder IN ('libx264', 'libx265', 'libvpx-vp9', 'libsvtav1', 'vvc')),  -- the encoder name
            enc_file TEXT,  -- name of the source video file
            enc_quality FLOAT CHECK(enc_quality >= 0.0 AND enc_quality <= 1.0),  -- normlize crf in [0, 1]
            enc_threads SMALLINT CHECK(enc_threads >= 0)  -- number of threads used
        )""")
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trigger_insert_env_act_unicity
            BEFORE INSERT ON t_env_environement
            BEGIN
                SELECT
                    CASE
                        WHEN NEW.env_act_id IN (
                            SELECT enc_act_id FROM t_enc_encode
                            UNION ALL SELECT dec_act_id FROM t_dec_decode
                            UNION ALL SELECT env_act_id FROM t_env_environement
                        ) THEN
                            RAISE (ABORT, 'act_id has to be unique')
                    END;
            END;
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trigger_update_env_act_unicity
            BEFORE UPDATE OF env_act_id ON t_env_environement
            BEGIN
                SELECT
                    CASE
                        WHEN NEW.env_act_id IN (
                            SELECT enc_act_id FROM t_enc_encode
                            UNION ALL SELECT dec_act_id FROM t_dec_decode
                            UNION ALL SELECT env_act_id FROM t_env_environement
                        ) THEN
                            RAISE (ABORT, 'act_id has to be unique')
                    END;
            END;
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trigger_insert_enc_act_unicity
            BEFORE INSERT ON t_enc_encode
            BEGIN
                SELECT
                    CASE
                        WHEN NEW.enc_act_id IN (
                            SELECT enc_act_id FROM t_enc_encode
                            UNION ALL SELECT dec_act_id FROM t_dec_decode
                            UNION ALL SELECT env_act_id FROM t_env_environement
                        ) THEN
                            RAISE (ABORT, 'act_id has to be unique')
                    END;
            END;
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trigger_insert_enc_act_unicity
            BEFORE UPDATE OF enc_act_id ON t_enc_encode
            BEGIN
                SELECT
                    CASE
                        WHEN NEW.enc_act_id IN (
                            SELECT enc_act_id FROM t_enc_encode
                            UNION ALL SELECT dec_act_id FROM t_dec_decode
                            UNION ALL SELECT env_act_id FROM t_env_environement
                        ) THEN
                            RAISE (ABORT, 'act_id has to be unique')
                    END;
            END;
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trigger_insert_dec_act_unicity
            BEFORE INSERT ON t_dec_decode
            BEGIN
                SELECT
                    CASE
                        WHEN NEW.dec_act_id IN (
                            SELECT enc_act_id FROM t_enc_encode
                            UNION ALL SELECT dec_act_id FROM t_dec_decode
                            UNION ALL SELECT env_act_id FROM t_env_environement
                        ) THEN
                            RAISE (ABORT, 'act_id has to be unique')
                    END;
            END;
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trigger_insert_dec_act_unicity
            BEFORE UPDATE OF dec_act_id ON t_dec_decode
            BEGIN
                SELECT
                    CASE
                        WHEN NEW.dec_act_id IN (
                            SELECT enc_act_id FROM t_enc_encode
                            UNION ALL SELECT dec_act_id FROM t_dec_decode
                            UNION ALL SELECT env_act_id FROM t_env_environement
                        ) THEN
                            RAISE (ABORT, 'act_id has to be unique')
                    END;
            END;
        """)
        cursor.close()


def is_sqlite(file: str | bytes | pathlib.Path):
    """Test if the provided path is an sqlite3 database.

    Examples
    --------
    >>> import os, pathlib, tempfile
    >>> from mendevi.database import create_database, is_sqlite
    >>> database = pathlib.Path(tempfile.mktemp())
    >>> is_sqlite(database)
    False
    >>> create_database(database)
    >>> is_sqlite(database)
    True
    >>> os.remove(database)
    >>>
    """
    file = pathlib.Path(file).expanduser().resolve()
    if not file.is_file():
        return False
    with open(file, "rb") as raw:
        header = raw.read(100)
    if len(header) < 100:  # SQLite database file header is 100 bytes
        return False
    return header.startswith(b"SQLite format 3")
