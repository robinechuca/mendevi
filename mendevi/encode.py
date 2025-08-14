#!/usr/bin/env python3

"""Perform encoding measures."""

import hashlib
import pathlib
import shlex
import shutil
import sqlite3
import subprocess
import tempfile

from mendevi.database.create import is_sqlite
from mendevi.database.serialize import list_to_binary, tensor_to_binary
from .utils import Activity
from .profiles import PROFILES


ENCODERS = ["libx264", "libx265", "libvpx-vp9", "libsvtav1", "vvc"]


def encode(src: pathlib.Path, *args, **kwargs) -> tuple[pathlib.Path, dict[str]]:
    """Transcode an existing video.

    Parameters
    ----------
    src : pathlib.Path
        The source video file to be transcoded.
    *args, **kwargs
        Transmitted to :py:func:`get_transcode_cmd`.

    Returns
    -------
    dst : pathlib.Path
        The transcoded video path. The stem is the md5 hash of the file content.
    cmd : str
        The ffmpeg command
    activity : dict[str]
        The computeur activity during the transcoding process.
    """
    assert isinstance(src, pathlib.Path), src.__class__.__name__
    assert src.is_file(), src

    # find tempfile name
    cmd = get_transcode_cmd(*args, **kwargs)
    signature = hashlib.md5(bytes(src) + (" ".join(cmd)).encode("utf-8")).hexdigest()
    dst = pathlib.Path(tempfile.gettempdir()) / f"{signature}.mp4"

    # transcode
    cmd = [
        "ffmpeg", "-y", "-hide_banner",
        "-i", str(src), "-c:v", *cmd,
        str(dst),
    ]
    with Activity() as activity:
        process = subprocess.run(cmd, check=True)

    # compute file hash
    with open(dst, "rb") as raw:
        signature = hashlib.file_digest(raw, "md5").hexdigest()

    # move file
    final_dst = src.parent / f"{signature}.mp4"
    if not final_dst.exists():
        shutil.copy(dst, src.parent / f"{signature}_partial.mp4")
        shutil.move(src.parent / f"{signature}_partial.mp4", final_dst)
    dst.unlink()

    cmd = " ".join(map(shlex.quote, cmd))
    return final_dst, cmd, activity


def encode_and_store(
    database: sqlite3.Cursor | str | bytes | pathlib.Path,
    env_id: int,
    src: pathlib.Path,
    **kwargs,
):
    """Transcode a video file and store the result in the database.

    Parameters
    ----------
    database : pathlike
        The path of the existing database to be updated.
    **kwargs
        Transmitted to :py:func:`encode`.

    Examples
    --------
    >>> import pathlib, tempfile
    >>> from mendevi.database.complete import add_environement
    >>> from mendevi.database.create import create_database
    >>> from mendevi.encode import encode_and_store
    >>> src = pathlib.Path("/data/dataset/video/despacito.mp4")
    >>> create_database(database := pathlib.Path(tempfile.mktemp(suffix=".sqlite")))
    >>> env_id = add_environement(database)
    >>> encode_and_store(
    ...     database, env_id, src, encoder="libx264", profile="sd", effort="fast", quality=0.5, threads=8
    ... )
    >>> database.unlink()
    >>>
    """
    # open database
    if not isinstance(database, sqlite3.Cursor):
        database = pathlib.Path(database).expanduser().resolve()
        assert is_sqlite(database), database
        with sqlite3.connect(database) as sql_database:
            # sql_database.execute("PRAGMA journal_mode=WAL")
            cursor = sql_database.cursor()
            res = encode_and_store(cursor, env_id, src, **kwargs)
            cursor.close()
            return res

    # transcode the video
    file, cmd, activity = encode(src, **kwargs)

    # fill video table
    vid_id = file.stem
    try:
        database.execute("INSERT INTO t_vid_video (vid_id) VALUES (?)", (vid_id,))
    except sqlite3.IntegrityError:
        pass

    # fill activity table
    activity = {
        "act_duration": activity["duration"],
        "act_ps_core": tensor_to_binary(activity["ps_cores"]),
        "act_ps_dt": list_to_binary(activity["ps_dt"]),
        "act_ps_ram": list_to_binary(activity["ps_ram"]),
        "act_rapl_dt": list_to_binary(activity.get("rapl_dt", None)),
        "act_rapl_power": list_to_binary(activity.get("rapl_powers", None)),
        "act_start": activity["start"],
        "act_wattmeter_dt": list_to_binary(activity.get("wattmeter_dt", None)),
        "act_wattmeter_power": list_to_binary(activity.get("wattmeter_powers", None)),
    }
    keys = list(activity)
    (act_id,) = database.execute(
        (
            f"INSERT INTO t_act_activity ({', '.join(keys)}) "
            f"VALUES ({', '.join('?'*len(keys))}) RETURNING act_id"
        ),
        [activity[k] for k in keys],
    ).fetchone()

    # fill encode table
    database.execute("""INSERT INTO t_enc_encode
        (
            enc_vid_id, enc_env_id, enc_act_id,
            enc_cmd, enc_effort, enc_encoder, enc_file, enc_profile, enc_quality, enc_quality, enc_threads
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            vid_id, env_id, act_id,
            cmd, kwargs["effort"], kwargs["encoder"], src.name, kwargs["profile"], kwargs["quality"], kwargs["threads"]
        )
    )


def get_transcode_cmd(
    encoder: str, profile: str, effort: str, quality: float, threads: int
) -> list[str]:
    """Return the ffmpeg encode cmd."""
    assert isinstance(encoder, str), encoder.__class__.__name__
    assert isinstance(profile, str), profile.__class__.__name__
    assert isinstance(effort, str), effort.__class__.__name__
    assert isinstance(quality, float), quality.__class__.__name__
    assert isinstance(threads, int), threads.__class__.__name__
    assert profile in PROFILES, profile
    assert effort in {"slow", "medium", "fast"}, effort
    assert 0.0 <= quality <= 1.0, quality
    assert threads > 0, threads

    def libsvtav1_lp(threads: int) -> int:
        """Convert threads in parralel level."""
        # https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/master/Source/Lib/Globals/enc_handle.c#L598
        # lp=1 -> threads=1
        # lp=2 -> threads=2
        # lp=3 -> threads=8
        # lp=4 -> threads=12
        # lp=5 -> threads=16
        # lp=6 -> threads=20
        lp = [1, 2, 3, 4, 5, 6]
        threads = [1, 2, 8, 12, 16, 20]
        plt.scatter(threads, lp)
        plt.show()
        return {  # threads to lp
            1: 1,
            2: 2, 3: 2, 4: 2, 5: 2,
            6: 3, 7: 3, 8: 3, 9: 3, 10: 3,
            11: 4, 12: 4, 13: 4, 14: 4,
            15: 5, 16: 5, 17: 5,
        }.get(threads, 6)

    match encoder:
        case "libx264":
            return [  # https://ffmpeg.party/x264/
                "libx264",
                "-crf", str(round(quality*51.0, 1)),
                "-preset", effort,
                "-tune", "ssim",
                "-threads", str(threads),
            ]
        case "libx265":
            return [   # https://x265.readthedocs.io/en/master/cli.html
                "libx265",
                "-crf", str(round(quality*51.0, 1)),
                "-preset", effort,
                "-tune", "ssim",
                "-x265-params",
                f"frame-threads={threads}:pools={threads}:wpp={1 if threads != 1 else 0}",
            ]
        case "libvpx-vp9":
            return [  # https://wiki.webmproject.org/ffmpeg/vp9-encoding-guide
                "libvpx-vp9",
                "-crf", str(round(quality*63.0)),
                "-speed", {"slow": "-2", "medium": "1", "fast": "8"}[effort],  # in [-16, 16]
                "-tune", "ssim",
                "-row-mt", "1", "-threads", str(threads),
            ]
        case "libsvtav1":
            return [
                "libsvtav1",
                "-crf", str(round(quality*63.0)),
                "-preset", {"slow": "4", "medium": "6", "fast": "8"}[effort],
                "-svtav1-params", f"film-grain=0:lp={libsvtav1_lp(threads)}",  # tune=2 broken in v3.0.2
                # "-threads", str(threads),
            ]
        case "vvc":
            bit = int(re.search(r"(?P<bit>\d+)le", PROFILES[profile]["pix_fmt"] + "8le")["bit"])
            return [
                "vvc",
                "-qp", str(round(quality*63.0)),
                "-preset", effort,
                "-qpa", "1",
                "-vvenc-params", f"internalbitdepth={bit}",
                "-threads", str(threads),
            ]

