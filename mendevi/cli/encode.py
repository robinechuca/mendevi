"""Perform encoding measures."""

import fractions
import hashlib
import inspect
import itertools
import math
import sqlite3
from typing import TYPE_CHECKING

import click
import numpy as np
from context_verbose import Printer

from mendevi.cst.encoders import ENCODERS
from mendevi.database.complete import add_environment
from mendevi.encode import encode_and_store
from mendevi.utils import compute_video_hash, get_pix_fmt, get_rate_video, get_resolution

from .parse import (
    CallBackType,
    CopyRamType,
    PixelParamType,
    ResolutionParamType,
    parse_videos_database,
)

if TYPE_CHECKING:
    import pathlib


def _parse_args(prt: Printer, kwargs: dict) -> None:
    """Verification of the arguments."""
    # repeat
    assert isinstance(kwargs["repeat"], int), kwargs["repeat"].__class__.__name__
    assert kwargs["repeat"] >= 1, kwargs["repeat"]
    prt.print(f"repeat    : {kwargs['repeat']}")

    # effort
    assert isinstance(kwargs["effort"], tuple), kwargs["effort"].__class__.__name__
    assert all(isinstance(p, str) for p in kwargs["effort"]), kwargs["effort"]
    assert all(p in {"fast", "medium", "slow"} for p in kwargs["effort"]), kwargs["effort"]
    prt.print(f"efforts   : {', '.join(kwargs['effort'])}")

    # encoder
    assert isinstance(kwargs["encoder"], tuple), kwargs["encoder"].__class__.__name__
    assert all(isinstance(e, str) for e in kwargs["encoder"]), kwargs["encoder"]
    assert all(e in ENCODERS for e in kwargs["encoder"]), kwargs["encoder"]
    prt.print(f"encoders  : {', '.join(kwargs['encoder'])}")

    # points
    assert isinstance(kwargs["points"], int), kwargs["points"].__class__.__name__
    assert kwargs["points"] >= 1, kwargs["points"]
    kwargs["quality"] = np.linspace(
        1.0/(kwargs["points"]+1),
        kwargs["points"]/(kwargs["points"]+1),
        kwargs["points"],
        dtype=np.float16,
    ).tolist()
    prt.print(f"qualities : k/{kwargs['points']+1}, k \u2208 [1, {kwargs['points']}]")

    # threads
    assert isinstance(kwargs["threads"], tuple), kwargs["threads"].__class__.__name__
    assert all(isinstance(t, int) for t in kwargs["threads"]), kwargs["threads"]
    assert all(t >= 1 for t in kwargs["threads"]), kwargs["threads"]
    prt.print(f"threads   : {', '.join(map(str, kwargs['threads']))}")

    # fps
    assert isinstance(kwargs["fps"], tuple), kwargs["fps"].__class__.__name__
    assert all(isinstance(f, fractions.Fraction) for f in kwargs["fps"]), kwargs["fps"]
    assert all(f > 0 for f in kwargs["fps"]), kwargs["fps"]
    kwargs["fps"] = [f.limit_denominator(1001) for f in kwargs["fps"]] or (None,)
    prt.print(
        f"fps       : {
            ', '.join(map(str, kwargs['fps'])) if kwargs['fps'] != (None,) else 'same as source'
        }",
    )

    # resolution
    assert isinstance(kwargs["resolution"], tuple), kwargs["resolution"].__class__.__name__
    assert all(
        isinstance(r, tuple) and len(r) == 2 and all(isinstance(s, int) and s > 0 for s in r)
        for r in kwargs["resolution"]
    ), kwargs["resolution"]
    prt.print(
        f"resolution: {
            ', '.join(f'w={w}:h={h}' for h, w in kwargs['resolution'])
            if kwargs['resolution'] else
            'same as source'
        }",
    )
    kwargs["resolution"] = kwargs["resolution"] or (None,)

    # pix_fmt
    assert isinstance(kwargs["pix_fmt"], tuple), kwargs["pix_fmt"].__class__.__name__
    assert all(isinstance(p, str) for p in kwargs["pix_fmt"]), kwargs["pix_fmt"]
    prt.print(
        f"pix_fmt   : {', '.join(kwargs['pix_fmt']) if kwargs['pix_fmt'] else 'same as source'}",
    )
    kwargs["pix_fmt"] = kwargs["pix_fmt"] or (None,)

    # mode
    assert isinstance(kwargs["mode"], tuple), kwargs["mode"].__class__.__name__
    assert all(isinstance(p, str) and p in {"cbr", "vbr"} for p in kwargs["mode"]), kwargs["mode"]
    kwargs["mode"] = tuple(sorted(set(kwargs["mode"])))
    prt.print(
        f"br mode   : {
            ' and '.join({'vbr': 'variable', 'cbr': 'constant'}[m] for m in kwargs['mode'])
        }",
    )

    # filter
    assert isinstance(kwargs["filter"], tuple), kwargs["filter"].__class__.__name__
    assert all(isinstance(f, str) for f in kwargs["filter"]), kwargs["filter"]
    prt.print(
        f"filters   : {', '.join(map(str, kwargs['filter'])) if kwargs['filter'] else 'no filter'}",
    )
    kwargs["filter"] =  kwargs["filter"] or (None,)

    # callback
    assert kwargs["callback"] is None or callable(kwargs["callback"])
    if kwargs["callback"]:
        prt.print(
            f"callback  : function {kwargs['callback'].__name__!r} "
            f"from {inspect.getfile(kwargs['callback'])!r}",
        )

    # ram
    assert isinstance(kwargs["ram"], float), kwargs["ram"].__class__.__name__
    prt.print(f"copy ram  : { {0.0: 'yes', math.inf: 'no'}.get(kwargs['ram'], kwargs['ram']) }")


@click.command()
@click.argument("videos", type=click.Path(), nargs=-1)
@click.option("-d", "--database", type=click.Path(), help="The database path.")
@click.option(
    "-r", "--repeat",
    type=int,
    default=2,
    help="The number of times the encoding is repeated on this machine.",
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
    default=["libx264", "libsvtav1"],
    multiple=True,
    help="The encoder name.",
)
@click.option(
    "-n", "--points",
    type=int,
    default=16,
    help="The number of quality point per encoder.",
)
@click.option(
    "-t", "--threads",
    type=int,
    default=[8],
    multiple=True,
    help="The number of threads used by encoders.",
)
@click.option(
    "-f", "--fps",
    type=fractions.Fraction,
    multiple=True,
    help="The optional framerate conversion during encoding.",
)
@click.option(
    "--resolution",
    type=ResolutionParamType(),
    multiple=True,
    help="The optional video shape conversion during encoding.",
)
@click.option(
    "--pix_fmt",
    type=PixelParamType(),
    multiple=True,
    help="The optional pixel format conversion during encoding.",
)
@click.option(
    "-m", "--mode",
    type=click.Choice(["cbr", "vbr"]),
    default=["vbr"],
    multiple=True,
    help="The optional bitrate mode (cbr or vbr).",
)
@click.option(
    "--filter",
    type=str,
    multiple=True,
    help="The ffmpeg filter to apply before encoding.",
)
@click.option(
    "--callback",
    type=CallBackType(),
    help="User defined function to adapt the cmd.",
)
@click.option(
    "--ram",
    type=CopyRamType(),
    default=2.0,
    help="'yes', 'no' or threshold: To manage video copy in ramdisk or local disk.",
)
def main(videos: tuple, database: str | None = None, **kwargs: dict) -> None:
    """Measures activity during encoding.

    \b
    Parameters
    ----------
    videos : tuple[pathlike]
        The source videos to be transcoded.
        It can be a glob expression, a directory or a file path.
    database : pathlike, optional
        The path to the database where all measurements are stored.
        If a folder is provided, the database is created inside this folder.
        By default, it is created right next to the video.
    **kwargs: dict
        Please refer to the detailed arguments below.
    repeat : int, default=2
        The number of times the experiment is repeated on this environment.
        This allows us to estimate the variance of measurements.
    effort : tuple[str], default=("medium",)
        The effort made to compress, `fast`, `medium` or `slow`.
    encoder : tuple[str], default=("libx264", "libsvtav1")
        The encoders and therefore the codecs to use.
        The available encoders are mendevi.cst.encoders.ENCODERS.
    points : int, default=16
        The number of different qualities to use.
        It is an indirect way to determine the CRF or the QP.
        The quality values are distributed evenly over ]0, 1[,
        for example, points=3 => qualities=[0.25, 0.5, 0.75].
    threads : int, default=8
        The theoretical number of threads used by the encoder.
        This roughly reflects the number of logical cores used.
    fps : fractions.Fraction, optional
        If provided, the reference video will be resampled on fly just before being encoded.
        This is therefore the frame rate of the transcoded video.
        If this argument is not provided, the frame rate remains unchanged.
    resolution : tuple[int, int], optional
        If provided, the reference video will be reshaped on fly just before being encoded.
        This is therefore the resolution of the transcoded video.
        If this argument is not provided, the resolution remains unchanged.
    pix_fmt : str, optional
        If provided, A pixel conversion is performed during encoding.
    mode : tuple[str]
        Text that is ``cbr`` if the bit rate is constant (cbr mode),
        or ``vbr`` if it is variable (constant quality mode).
    filter : str, optional
        A video ffmpeg filter (after -vf) which applies at the time of transcoding,
        more precisely between decoding and conversion. It is a kind of pre-conversion.
    callback : str, optional
        The name of the custom function to change the cmd, the signature must match:
        def any(cmd: CmdFFMPEG, **kwargs) -> list[str] | str:
            ...
    ram : float
        The threshold for deciding where to copy videos. Copy in /dev/shm if
        ``available_ram_memory > ram * video_size``, otherwise, copy to the /tmp folder.

    """
    with Printer("Parse configuration...") as prt:
        videos, database = parse_videos_database(prt, videos, database)
        assert videos, "at least one video is required"
        _parse_args(prt, kwargs)

    # preparation of context
    env_id = add_environment(database)
    kwargs["src_vid_id"]: dict[pathlib.Path, bytes] = compute_video_hash(videos)

    keys = [
        "effort", "encoder", "filter", "fps", "mode", "pix_fmt", "quality", "resolution", "threads",
    ]

    # retrieves the settings for videos that have already been transcoded
    with sqlite3.connect(database) as conn, Printer("Search already done...") as prt:
        conn.row_factory = sqlite3.Row
        done: dict[tuple, int] = {}
        for row in conn.execute(
            "SELECT * FROM t_enc_encode WHERE enc_env_id=?", (env_id,),
        ):
            values = {
                "effort": row["enc_effort"],
                "encoder": row["enc_encoder"],
                "filter": row["enc_filter"] or None,
                "fps": fractions.Fraction(row["enc_fps"]).limit_denominator(1001),
                "mode": row["enc_mode"],
                "pix_fmt": row["enc_pix_fmt"],
                "quality": float(row["enc_quality"]),
                "resolution": (row["enc_height"], row["enc_width"]),
                "src_vid_id": row["enc_src_vid_id"],
                "threads": row["enc_threads"],
            }
            values = tuple(values[k] for k in ["src_vid_id", *keys])
            done[values] = done.get(values, 0) + 1
        prt.print(f"{sum(done.values())} video already encoded under these environment")

    # iterate on all parameters
    loops = sorted(
        itertools.product(videos, *(kwargs[k] for k in keys)),
        key=lambda t: hashlib.md5(str(t).encode("utf-8")).hexdigest(),  # repetable shuffle
    )
    for i, (repeat, values_) in enumerate(itertools.product(range(kwargs["repeat"]), loops)):
        values = dict(zip(["video", *keys], values_, strict=True), repeat=values_[0])
        values["repeat"] = repeat
        values["fps"] = values["fps"] or get_rate_video(values["video"])
        values["pix_fmt"] = values["pix_fmt"] or get_pix_fmt(values["video"])
        values["resolution"] = values["resolution"] or get_resolution(values["video"])
        values["src_vid_id"] = kwargs["src_vid_id"][values["video"]]
        values["callback"] = kwargs["callback"]
        key = (values["src_vid_id"], *tuple(values[k] for k in keys))
        if done.get(key, 0) > values["repeat"]:
            continue
        with Printer(f"Encode {i+1}/{kwargs["repeat"]*len(loops)}...", color="cyan") as prt:
            encode_and_store(database, env_id, values.pop("video"), ram=kwargs["ram"], **values)
            done[key] = done.get(key, 0) + 1
            prt.print_time()
