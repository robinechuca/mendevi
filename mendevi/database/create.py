#!/usr/bin/env python3

"""Initialize the SQL database."""

import pathlib
import sqlite3


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
        cursor.execute("""CREATE TABLE environement (
            id INTEGER PRIMARY KEY,

            /* CONTEXT DETAILS */
            ffmpeg MEDIUMTEXT,  -- result of 'ffmpeg -version'
            hostname TEXT,  -- node name
            hostnamectl MEDIUMTEXT,  -- result of 'hostnamectl'
            lshw MEDIUMTEXT,  -- result of 'lshw'
            pip MEDIUMTEXT,  -- result of 'pip freeze'
            pyav MEDIUMTEXT  -- av.library_versions

            /* IDLE MEASURES */
            start TIMESTAMP,  -- absolute start timestamp
            duration FLOAT CHECK(duration > 0.0),  -- full encoding time in seconds
            rapl_dt LONGBLOB,  -- list of the duration of each interval in seconds
            rapl_power LONGBLOB,  -- list of the average power in watt in each interval
            wattmeter_dt LONGBLOB,  -- list of the duration of each interval in seconds
            wattmeter_power LONGBLOB,  -- list of the sampled power in watt in each point
            ps_dt LONGBLOB,  -- list of the duration of each interval in seconds
            ps_core LONGBLOB,  -- tensor of detailed usage of each logical core in %
            ps_ram LONGBLOB  -- list of the sampled ram usage in bytes in each point
        )""")
        cursor.execute("""CREATE TABLE video (
            id INTEGER PRIMARY KEY,
            hash BLOB NOT NULL,  -- md5 hash of the video

            /* VIDEO CONTENT */
            height SMALLINT CHECK(height > 0),  -- display height
            width SMALLINT CHECK(width > 0),  -- display width
            eotf TINYTEXT,  -- name of the electro optical transfer function
            gamut TINYTEXT,  -- name of the color space
            subsampling TINYTEXT CHECK(subsampling IN ('444', '422', '420')),  -- yuv pixel subsampling
            codec TINYTEXT,  -- the codec name
            duration FLOAT CHECK(duration > 0.0),  -- video duration in second
            size BIGINT CHECK(width >= 0),  -- file size in bytes
            frames LONGBLOB,  -- serialized version of the metadata of all frames

            /* METRICS */
            lpips_alex LONGBLOB,  -- list lpips with alex for each frame
            lpips_vgg LONGBLOB,  -- list lpips with vgg for each frame
            psnr LONGBLOB,  -- list of the psnr (6, 1, 1) metric for each frame
            ssim LONGBLOB,  -- list of the ssim (6, 1, 1) metric for each frame, gauss win 11x11
            uvq LONGBLOB  -- list of the google uvq metric for each second of video
        )""")
        cursor.execute("""CREATE TABLE decode (
            id INTEGER PRIMARY KEY,
            video_id INTEGER REFERENCES video(id),  -- link to video table
            environement_id INTEGER REFERENCES environement(id),  -- link to environement table

            /* MEASURES */
            start TIMESTAMP,  -- absolute start timestamp
            duration FLOAT CHECK(duration > 0.0),  -- full encoding time in seconds
            rapl_dt LONGBLOB,  -- list of the duration of each interval in seconds
            rapl_power LONGBLOB,  -- list of the average power in watt in each interval
            wattmeter_dt LONGBLOB,  -- list of the duration of each interval in seconds
            wattmeter_power LONGBLOB,  -- list of the sampled power in watt in each point
            ps_dt LONGBLOB,  -- list of the duration of each interval in seconds
            ps_core LONGBLOB,  -- tensor of detailed usage of each logical core in %
            ps_ram LONGBLOB  -- list of the sampled ram usage in bytes in each point
        )""")
        cursor.execute("""CREATE TABLE encode (
            id INTEGER PRIMARY KEY,
            video_id INTEGER REFERENCES video(id),  -- link to video table
            environement_id INTEGER REFERENCES environement(id),  -- link to environement table

            /* TASK DESCRIPTION */
            cmd TEXT NOT NULL,  -- exact ffmpeg command used
            effort TINYTEXT,  -- equivalent preset used for encoding
            encoder TINYTEXT,  -- the encoder name
            file TEXT,  -- stem name of the source video file
            fps FLOAT,  -- framerate of the encoded video
            profile TINYTEXT,  -- general profile used
            quality FLOAT,  -- normlize crf in [0, 1]
            threads SMALLINT,  -- number of threads used

            /* MEASURES */
            start TIMESTAMP,  -- absolute start timestamp
            duration FLOAT CHECK(duration > 0.0),  -- full encoding time in seconds
            rapl_dt LONGBLOB,  -- list of the duration of each interval in seconds
            rapl_power LONGBLOB,  -- list of the average power in watt in each interval
            wattmeter_dt LONGBLOB,  -- list of the duration of each interval in seconds
            wattmeter_power LONGBLOB,  -- list of the sampled power in watt in each point
            ps_dt LONGBLOB,  -- list of the duration of each interval in seconds
            ps_core LONGBLOB,  -- tensor of detailed usage of each logical core in %
            ps_ram LONGBLOB  -- list of the sampled ram usage in bytes in each point
        )""")
        cursor.close()

