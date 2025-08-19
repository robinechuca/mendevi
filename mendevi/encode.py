#!/usr/bin/env python3

"""Perform encoding measures."""

import fractions
import hashlib
import itertools
import pathlib
import re
import shlex
import shutil
import sqlite3
import subprocess
import tempfile

from context_verbose import Printer
import click
import cutcutcodec
import numpy as np
import tqdm

from mendevi.database.complete import add_environement
from mendevi.database.create import create_database, is_sqlite
from mendevi.database.serialize import list_to_binary, tensor_to_binary
from .utils import Activity
from .profiles import PROFILES


ENCODERS = {"libx264", "libx265", "libvpx-vp9", "libsvtav1", "vvc"}


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
        The transcoded video path. The stem contains the md5 hash of the file content.
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

    # display
    with Printer(f"Execute: <{' '.join(map(shlex.quote, cmd))}>...", color="white") as prt:
        prt.print(f"input video: {src.name}")
        duration = round(float(cutcutcodec.get_duration_video(src)), 2)
        load = tqdm.tqdm(
            dynamic_ncols=True,
            leave=False,
            smoothing=1e-2,
            total=duration,
            unit="s",
        )

        # transcode
        cmd = [
            "ffmpeg", "-y", "-hide_banner",
            "-i", str(src), "-c:v", *cmd,
            str(dst),
        ]
        with Activity() as activity, subprocess.Popen(cmd, stderr=subprocess.PIPE) as process:
            out = b""
            is_finish = False
            while not is_finish:
                while (
                    match := re.search(br"time=(?P<h>\d+):(?P<m>\d{1,2}):(?P<s>\d{1,2}\.\d*)", out)
                ) is None:
                    if not (buff := process.stderr.read(32)):
                        is_finish = True
                        break
                    out += buff
                else:
                    out = out[match.endpos:]
                    elapsed = round(
                        3600.0*float(match["h"]) + 60.0*float(match["m"]) + float(match["s"]),
                        2,
                    )
                    load.total = max(load.total, elapsed)
                    load.update(elapsed-load.n)
            load.close()
            if process.returncode:
                raise RuntimeError(f"failed to execute {cmd}")

        # print
        prt.print(f"avg cpu usage: {activity['ps_core']:.1f} %")
        prt.print(f"avg ram usage: {1e-9*np.mean(activity['ps_ram']):.2g} Go")
        if "rapl_power" in activity:
            prt.print(f"avg rapl power: {activity['rapl_power']:.2g} W")
        if "wattmeter_power" in activity:
            prt.print(f"avg wattmeter power: {activity['wattmeter_power']:.2g} W")

        # compute file hash
        with open(dst, "rb") as raw:
            signature = hashlib.file_digest(raw, "md5").hexdigest()
        prt.print(f"output video: sample_{signature}.mp4")

    # move file
    final_dst = src.parent / f"sample_{signature}.mp4"
    if not final_dst.exists():
        shutil.copy(dst, src.parent / f"sample_{signature}_partial.mp4")
        shutil.move(src.parent / f"sample_{signature}_partial.mp4", final_dst)
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
    vid_id = re.search(r"[0-9a-f]{32}", file.stem).group()
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
            enc_cmd, enc_effort, enc_encoder, enc_file, enc_quality, enc_threads
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            vid_id, env_id, act_id,
            cmd, kwargs["effort"], kwargs["encoder"], src.name, kwargs["quality"], kwargs["threads"]
        )
    )


def get_transcode_cmd(
    encoder: str, effort: str, quality: float, threads: int
) -> list[str]:
    """Return the ffmpeg encode cmd."""
    assert isinstance(encoder, str), encoder.__class__.__name__
    assert encoder in ENCODERS, encoder
    assert isinstance(effort, str), effort.__class__.__name__
    assert isinstance(quality, float), quality.__class__.__name__
    assert isinstance(threads, int), threads.__class__.__name__
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
            profile = "uhd"  # TODO: détecter automatiquement grace a la video source
            bit = int(re.search(r"(?P<bit>\d+)le", PROFILES[profile]["pix_fmt"] + "8le")["bit"])
            return [
                "vvc",
                "-qp", str(round(quality*63.0)),
                "-preset", effort,
                "-qpa", "1",
                "-vvenc-params", f"internalbitdepth={bit}",
                "-threads", str(threads),
            ]


@click.command()
@click.argument("videos", type=click.Path(), nargs=-1)
@click.option("-d", "--database", type=click.Path(), help="The database path.")
@click.option(
    "-r", "--repeat",
    type=int,
    default=2,
    help="The number of times the experiment is repeated.",
)
@click.option(
    "-e", "--effort",
    type=click.Choice(["fast", "medium", "slow"]),
    default=["medium"],
    multiple=True,
    help="The compression effort (default = medium).",
)
@click.option(
    "-c", "--encoder",
    type=click.Choice(sorted(ENCODERS)),
    default=sorted(ENCODERS),
    multiple=True,
    help="The encoder name.",
)
@click.option(
    "-n", "--points",
    type=int,
    default=24,
    help="The number of quality point per encoder.",
)
@click.option(
    "-t", "--threads",
    type=int,
    default=[8],
    multiple=True,
    help="The number of threads used by encoders.",
)
def main(videos: tuple, database: str = None, **kwargs):
    """Measures activity during encoding.

    \b
    Parameters
    ----------
    videos : tuple[pathlike]
        The source videos to be transcoded.
    database : pathlike, optional
        The path to the database where all measurements are stored.
        By default, it is created right next to the video.
    repeat : int, default=2
        The number of times the experiment is repeated.
        This allows us to estimate the variance of measurements.
    effort : tuple[str], default=("medium",)
        The effort made to compress, `fast`, `medium` or `slow`.
    encoder : tuple[str], default=("libsvtav1", "libvpx-vp9", "libx264", "libx265", "vvc")
        The encoders and therefore the codecs to use.
    points : int, default=24
        The number of different qualities to use.
        It is an indirect way to determine the CRF or the QP.
        The quality values are distributed evenly over ]0, 1[,
        for example, points=3 => qualities=[0.25, 0.5, 0.75].
    threads : int, default=8
        The theoretical number of threads used by the encoder.
        This roughly reflects the number of logical cores used.
    """
    with Printer("Parse configuration...") as prt:
        # video
        assert isinstance(videos, tuple), videos.__class__.__name__
        assert videos, "at least one video is required"
        videos = [pathlib.Path(v).expanduser() for v in videos]
        assert all(v.is_file() for v in videos), videos
        prt.print(f"videos   : {', '.join(map(str, videos))}")

        # database
        database = pathlib.Path(database or videos[0].parent / "mendevi.db").expanduser()
        if not database.exists():
            create_database(database)
        prt.print(f"database : {database}")

        # repeat
        assert "repeat" in kwargs, sorted(kwargs)
        assert isinstance(kwargs["repeat"], int), kwargs["repeat"].__class__.__name__
        assert kwargs["repeat"] >= 1, kwargs["repeat"]
        prt.print(f"repeat   : {kwargs['repeat']}")

        # effort
        assert "effort" in kwargs, sorted(kwargs)
        assert isinstance(kwargs["effort"], tuple), kwargs["effort"].__class__.__name__
        assert all(isinstance(p, str) for p in kwargs["effort"]), kwargs["effort"].__class__.__name__
        assert all(p in {"fast", "medium", "slow"} for p in kwargs["effort"]), kwargs["effort"]
        prt.print(f"efforts  : {', '.join(kwargs['effort'])}")

        # encoder
        assert "encoder" in kwargs, sorted(kwargs)
        assert isinstance(kwargs["encoder"], tuple), kwargs["encoder"].__class__.__name__
        assert all(isinstance(e, str) for e in kwargs["encoder"]), kwargs["encoder"].__class__.__name__
        assert all(e in ENCODERS for e in kwargs["encoder"]), kwargs["encoder"]
        prt.print(f"encoders : {', '.join(kwargs['encoder'])}")

        # points
        assert "points" in kwargs, sorted(kwargs)
        assert isinstance(kwargs["points"], int), kwargs["points"].__class__.__name__
        assert kwargs["points"] >= 1, kwargs["points"]
        kwargs["quality"] = [
            fractions.Fraction(i+1, kwargs["points"]+2)
            for i in range(kwargs["points"])
        ]
        prt.print(f"qualities: k * {kwargs['quality'][0]}, k \u2208 [1, {kwargs['points']}]")
        kwargs["quality"] = list(map(float, kwargs["quality"]))

        # threads
        assert "threads" in kwargs, sorted(kwargs)
        assert isinstance(kwargs["threads"], tuple), kwargs["threads"].__class__.__name__
        assert all(isinstance(t, int) for t in kwargs["threads"]), kwargs["threads"].__class__.__name__
        assert all(t >= 1 for t in kwargs["threads"]), kwargs["threads"]
        prt.print(f"threads  : {', '.join(map(str, kwargs['threads']))}")

    # retrieves the settings for videos that have already been transcoded
    env_id = add_environement(database)
    with sqlite3.connect(database) as sql_database:
        # sql_database.execute("PRAGMA journal_mode=WAL")
        done: dict[tuple, int] = {}
        for key in sql_database.execute(
            """
            SELECT enc_effort, enc_encoder, enc_file, enc_quality, enc_threads
            FROM t_enc_encode WHERE enc_env_id=?
            """,
            (env_id,)
        ):
            done[key] = done.get(key, 0) + 1

    # iterate on all the parameters
    nbr = (
        kwargs["repeat"]
        * len(kwargs["threads"])
        * len(kwargs["effort"])
        * kwargs["points"]
        * len(kwargs["encoder"])
    )
    for i, (repeat, video, threads, effort, quality, encoder) in enumerate(
        itertools.product(
            range(kwargs["repeat"]),
            videos,
            kwargs["threads"],
            kwargs["effort"],
            kwargs["quality"],
            kwargs["encoder"],
        )
    ):
        key = (effort, encoder, video.name, quality, threads)
        if done.get(key, 0) > repeat:
            continue
        with Printer(
            (
                f"Encode {i}/{nbr}: "
                f"video={video.name}, "
                f"threads={threads}, "
                f"effort={effort}, "
                f"quality={quality:.2f}, "
                f"encoder={encoder}..."
            ),
            color="cyan",
        ) as prt:
            encode_and_store(
                database, env_id, video,
                threads=threads, effort=effort, quality=quality, encoder=encoder,
            )
            done[key] = done.get(key, 0) + 1
            prt.print_time()
