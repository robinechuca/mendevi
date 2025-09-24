#!/usr/bin/env python3

"""Initialize the SQL database."""

import pathlib
import sqlite3


ENV_UNIQUE = [
    "env_ffmpeg_version",
    "env_hostname",
    "env_logical_cores",
    # "env_pip_freeze",
    "env_processor",
]


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
            vid_name TEXT,  -- the path video name

            /* VIDEO CONTENT */
            vid_codec TINYTEXT,  -- the codec name
            vid_duration FLOAT CHECK(vid_duration > 0.0),  -- video duration in second
            vid_eotf TINYTEXT,  -- name of the electro optical transfer function
            vid_fps FLOAT CHECK(vid_fps > 0.0),  -- theorical framerate of the video
            vid_frames LONGTEXT,  -- json serialized version of the metadata of all frames
            vid_gamut TINYTEXT,  -- name of the color space
            vid_height SMALLINT CHECK(vid_height > 0),  -- display height
            vid_pix_fmt TINYTEXT,  -- the name of the pixel format
            vid_size BIGINT CHECK(vid_width >= 0),  -- file size in bytes
            vid_width SMALLINT CHECK(vid_width > 0),  -- display width

            /* NON COMPARATIVE METRICS */
            vid_uvq LONGBLOB  -- list of the google uvq metric for each second of video
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS t_met_metric (
            met_id INTEGER PRIMARY KEY AUTOINCREMENT,
            met_ref_vid_id BINARY(128) NOT NULL,  -- link to the reference video
            met_dis_vid_id BINARY(128) NOT NULL,  -- link to the distorded video

            /*  COMPARATIVE METRICS */
            met_lpips_alex LONGBLOB,  -- list lpips with alex for each frame
            met_lpips_vgg LONGBLOB,  -- list lpips with vgg for each frame
            met_psnr LONGBLOB,  -- list of the psnr (6, 1, 1) metric for each frame
            met_ssim LONGBLOB,  -- list of the ssim (6, 1, 1) metric for each frame, gauss win 11x11
            met_vmaf LONGBLOB,  -- list of the vmaf metric for each frame

            UNIQUE(met_ref_vid_id, met_dis_vid_id) ON CONFLICT FAIL
        )""")
        cursor.execute(f"""CREATE TABLE IF NOT EXISTS t_env_environment (
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
            env_idle_act_id INTEGER REFERENCES t_act_activity(act_id),  -- link to activity table

            /* CONSTRAINTS */
            UNIQUE({", ".join(ENV_UNIQUE)}) ON CONFLICT FAIL
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS t_dec_decode (
            dec_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dec_vid_id BINARY(128) NOT NULL REFERENCES t_vid_video(vid_id) ON DELETE CASCADE,  -- link to video table
            dec_env_id INTEGER NOT NULL REFERENCES t_env_environment(env_id) ON DELETE CASCADE,  -- link to environment table
            dec_act_id INTEGER REFERENCES t_act_activity(act_id),  -- link to activity table
            dec_cmd TEXT,  -- exact ffmpeg command used
            dec_filter TEXT,  -- ffmpeg additional video filter
            dec_height SMALLINT CHECK(dec_height > 0),  -- display resolution
            dec_pix_fmt TINYTEXT,  -- display pixel format
            dec_width SMALLINT CHECK(dec_width > 0)  -- display resolution
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS t_enc_encode (
            enc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            enc_src_vid_id BINARY(128) REFERENCES t_vid_video(vid_id),  -- link to video table, src video
            enc_dst_vid_id BINARY(128) NOT NULL REFERENCES t_vid_video(vid_id) ON DELETE CASCADE,  -- link to video table, dst video
            enc_env_id INTEGER NOT NULL REFERENCES t_env_environment(env_id) ON DELETE CASCADE,  -- link to environment table
            enc_act_id INTEGER REFERENCES t_act_activity(act_id),  -- link to activity table

            /* TASK DESCRIPTION */
            enc_cmd TEXT,  -- exact ffmpeg command used
            enc_effort TINYTEXT CHECK(enc_effort IN ('fast', 'medium', 'slow')),  -- equivalent preset used for encoding
            enc_encoder TINYTEXT CHECK(enc_encoder IN ('libx264', 'libx265', 'libvpx-vp9', 'libsvtav1', 'vvc')),  -- the encoder name
            enc_filter TEXT,  -- ffmpeg additional video filter
            enc_fps FLOAT CHECK(enc_fps > 0.0),  -- target conversion fps
            enc_height SMALLINT CHECK(enc_height > 0),  -- target conversion resolution
            enc_pix_fmt TINYTEXT,  -- target conversion pixel format
            enc_quality FLOAT CHECK(enc_quality >= 0.0 AND enc_quality <= 1.0),  -- normlize crf in [0, 1]
            enc_threads SMALLINT CHECK(enc_threads >= 0),  -- number of threads used
            enc_vbr BOOLEAN CHECK(enc_vbr IN (0, 1)),  -- the bit rate mode
            enc_width SMALLINT CHECK(enc_width > 0)  -- target conversion resolution
        )""")
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trigger_insert_env_act_unicity
            BEFORE INSERT ON t_env_environment
            BEGIN
                SELECT
                    CASE
                        WHEN NEW.env_idle_act_id IN (
                            SELECT enc_act_id FROM t_enc_encode
                            UNION ALL SELECT dec_act_id FROM t_dec_decode
                            UNION ALL SELECT env_idle_act_id FROM t_env_environment
                        ) THEN
                            RAISE (ABORT, 'act_id has to be unique')
                    END;
            END;
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trigger_update_env_act_unicity
            BEFORE UPDATE OF env_idle_act_id ON t_env_environment
            BEGIN
                SELECT
                    CASE
                        WHEN NEW.env_idle_act_id IN (
                            SELECT enc_act_id FROM t_enc_encode
                            UNION ALL SELECT dec_act_id FROM t_dec_decode
                            UNION ALL SELECT env_idle_act_id FROM t_env_environment
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
                            UNION ALL SELECT env_idle_act_id FROM t_env_environment
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
                            UNION ALL SELECT env_idle_act_id FROM t_env_environment
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
                            UNION ALL SELECT env_idle_act_id FROM t_env_environment
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
                            UNION ALL SELECT env_idle_act_id FROM t_env_environment
                        ) THEN
                            RAISE (ABORT, 'act_id has to be unique')
                    END;
            END;
        """)

    filename.chmod(0o777)


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
    file = pathlib.Path(file).expanduser()
    if not file.is_file():
        return False
    with open(file, "rb") as raw:
        header = raw.read(100)
    if len(header) < 100:  # SQLite database file header is 100 bytes
        return False
    return header.startswith(b"SQLite format 3")
