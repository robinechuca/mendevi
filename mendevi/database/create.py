"""Initialize the SQL database."""

import pathlib
import sqlite3

ENV_UNIQUE = [
    "env_ffmpeg_version",
    "env_hostname",
    "env_logical_cores",
    "env_processor",
]

SQL_HEADER_SIZE = 100  # SQLite database file header is 100 bytes


def create_database(filename: str | bytes | pathlib.Path) -> None:
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

    with sqlite3.connect(filename) as conn:
        # next line can fail flush
        # conn.execute("PRAGMA journal_mode=WAL")  # reduce "database is locked"
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS t_act_activity (
            act_id INTEGER PRIMARY KEY AUTOINCREMENT,

            /* MEASURES */
            act_start TIMESTAMP NOT NULL,
            act_duration FLOAT NOT NULL CHECK(act_duration > 0.0),
            act_rapl_dt LONGBLOB,
            act_rapl_power LONGBLOB,
            act_wattmeter_dt LONGBLOB,
            act_wattmeter_power LONGBLOB,
            act_gpu_dt LONGBLOB,
            act_gpu_power LONGBLOB,
            act_ps_dt LONGBLOB,
            act_ps_core LONGBLOB,
            act_ps_temp LONGBLOB,
            act_ps_ram LONGBLOB
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS t_vid_video (
            vid_id BINARY(128) PRIMARY KEY,
            vid_name TEXT,

            /* VIDEO CONTENT */
            vid_codec TINYTEXT,
            vid_duration FLOAT CHECK(vid_duration > 0.0),
            vid_eotf TINYTEXT,
            vid_fps FLOAT CHECK(vid_fps > 0.0),
            vid_frames LONGTEXT,
            vid_gamut TINYTEXT,
            vid_height SMALLINT CHECK(vid_height > 0),
            vid_pix_fmt TINYTEXT,
            vid_range TINYTEXT CHECK(vid_range IN ('pc', 'tv')),
            vid_size BIGINT CHECK(vid_width >= 0),
            vid_width SMALLINT CHECK(vid_width > 0),

            /* NON COMPARATIVE METRICS */
            vid_rms_sobel LONGBLOB,
            vid_rms_time_diff LONGBLOB,
            vid_uvq LONGBLOB
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS t_met_metric (
            met_id INTEGER PRIMARY KEY AUTOINCREMENT,
            met_ref_vid_id BINARY(128) NOT NULL,
            met_dis_vid_id BINARY(128) NOT NULL,

            /*  COMPARATIVE METRICS */
            met_lpips_alex LONGBLOB,
            met_lpips_vgg LONGBLOB,
            met_psnr LONGBLOB,
            met_ssim LONGBLOB,
            met_vif LONGBLOB,
            met_vmaf LONGBLOB,

            UNIQUE(met_ref_vid_id, met_dis_vid_id) ON CONFLICT FAIL
        )""")
        cursor.execute(f"""CREATE TABLE IF NOT EXISTS t_env_environment (
            env_id INTEGER PRIMARY KEY AUTOINCREMENT,

            /* CONTEXT DETAILS */
            env_ffmpeg_version MEDIUMTEXT NOT NULL,
            env_hostname TINYTEXT NOT NULL,
            env_kernel_version TINYTEXT,
            env_librav1e_version MEDIUMTEXT,
            env_libsvtav1_version MEDIUMTEXT,
            env_libvpx_vp9_version MEDIUMTEXT,
            env_libx265_version MEDIUMTEXT,
            env_logical_cores INTEGER NOT NULL CHECK(env_logical_cores > 0),
            env_lshw LONGTEXT,
            env_lspci LONGTEXT,
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
            dec_vid_id BINARY(128) NOT NULL REFERENCES t_vid_video(vid_id) ON DELETE CASCADE,
            dec_env_id INTEGER NOT NULL REFERENCES t_env_environment(env_id) ON DELETE CASCADE,
            dec_act_id INTEGER REFERENCES t_act_activity(act_id),
            dec_cmd TEXT,
            dec_decoder TINYTEXT,
            dec_filter TEXT,
            dec_height SMALLINT CHECK(dec_height > 0),
            dec_log LONGTEXT,
            dec_pix_fmt TINYTEXT,
            dec_width SMALLINT CHECK(dec_width > 0)
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS t_enc_encode (
            enc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            enc_src_vid_id BINARY(128) REFERENCES t_vid_video(vid_id),
            enc_dst_vid_id BINARY(128) NOT NULL REFERENCES t_vid_video(vid_id) ON DELETE CASCADE,
            enc_env_id INTEGER NOT NULL REFERENCES t_env_environment(env_id) ON DELETE CASCADE,
            enc_act_id INTEGER REFERENCES t_act_activity(act_id),

            /* TASK DESCRIPTION */
            enc_cmd TEXT,  -- exact ffmpeg command used
            enc_effort TINYTEXT CHECK(enc_effort IN ('fast', 'medium', 'slow')),
            enc_encoder TINYTEXT,
            enc_filter TEXT,
            enc_fps FLOAT CHECK(enc_fps > 0.0),
            enc_height SMALLINT CHECK(enc_height > 0),
            enc_log LONGTEXT,
            enc_mode TINYTEXT CHECK(enc_mode IN ('cbr', 'vbr')),
            enc_pix_fmt TINYTEXT,
            enc_quality FLOAT CHECK(enc_quality >= 0.0 AND enc_quality <= 1.0),
            enc_threads SMALLINT CHECK(enc_threads >= 0),
            enc_width SMALLINT CHECK(enc_width > 0)
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


def is_sqlite(file: str | bytes | pathlib.Path) -> bool:
    """Test if the provided path is an sqlite3 database.

    Examples
    --------
    >>> import os, pathlib, tempfile
    >>> from mendevi.database.create import create_database, is_sqlite
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
    with file.open("rb") as raw:
        header = raw.read(SQL_HEADER_SIZE)
    if len(header) < SQL_HEADER_SIZE:
        return False
    return header.startswith(b"SQLite format 3")
