#!/usr/bin/env python3

"""Perform encoding measures."""

import fractions
import functools
import itertools
import operator
import pathlib
import re
import sqlite3

from context_verbose import Printer
import click
import cutcutcodec
import numpy as np

from mendevi.database.complete import add_environement
from mendevi.database.create import create_database
from mendevi.encode import encode_and_store
from mendevi.utils import get_pxl_format, get_rate_video, get_resolution



ENCODERS = {"libx264", "libx265", "libvpx-vp9", "libsvtav1", "vvc"}



class PixelParamType(click.ParamType):
    """Parse the pixel format."""
    name = "pixel"

    def convert(self, value, param, ctx):
        value = value.lower()
        if not re.fullmatch(r"yuv4[24][024]p(?:10le|12le)?", value):
            self.fail(f"{value!r} is not a valid pixel format", param, ctx)
        return value


class ResolutionParamType(click.ParamType):
    """Parse the resolution."""
    name = "resolution"

    def convert(self, value, param, ctx):
        if (match := re.search(
            r"(?P<t1>he)?\D*(?P<d1>\d+)\D+?(?P<t2>w)?\D*(?P<d2>\d+)", value.lower()
        )) is None:
            self.fail(f"{value!r} is not a valid video shape", param, ctx)
        if match["t1"] == "he" or match["t2"] == "w":
            return (int(match["d1"]), int(match["d2"]))
        return (int(match["d2"]), int(match["d1"]))


def _parse_args(prt: Printer, kwargs: dict):
    """Verification of the arguments."""
    # repeat
    assert "repeat" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["repeat"], int), kwargs["repeat"].__class__.__name__
    assert kwargs["repeat"] >= 1, kwargs["repeat"]
    prt.print(f"repeat    : {kwargs['repeat']}")

    # effort
    assert "effort" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["effort"], tuple), kwargs["effort"].__class__.__name__
    assert all(isinstance(p, str) for p in kwargs["effort"]), kwargs["effort"]
    assert all(p in {"fast", "medium", "slow"} for p in kwargs["effort"]), kwargs["effort"]
    prt.print(f"efforts   : {', '.join(kwargs['effort'])}")

    # encoder
    assert "encoder" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["encoder"], tuple), kwargs["encoder"].__class__.__name__
    assert all(isinstance(e, str) for e in kwargs["encoder"]), kwargs["encoder"]
    assert all(e in ENCODERS for e in kwargs["encoder"]), kwargs["encoder"]
    prt.print(f"encoders  : {', '.join(kwargs['encoder'])}")

    # points
    assert "points" in kwargs, sorted(kwargs)
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
    assert "threads" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["threads"], tuple), kwargs["threads"].__class__.__name__
    assert all(isinstance(t, int) for t in kwargs["threads"]), kwargs["threads"]
    assert all(t >= 1 for t in kwargs["threads"]), kwargs["threads"]
    prt.print(f"threads   : {', '.join(map(str, kwargs['threads']))}")

    # fps
    assert "fps" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["fps"], tuple), kwargs["fps"].__class__.__name__
    assert all(isinstance(f, fractions.Fraction) for f in kwargs["fps"]), kwargs["fps"]
    assert all(f > 0 for f in kwargs["fps"]), kwargs["fps"]
    if kwargs["fps"]:
        kwargs["fps"] = [f.limit_denominator(1001) for f in kwargs["fps"]]
        prt.print(f"fps       : {', '.join(map(str, kwargs['fps']))}")
    else:
        kwargs["fps"] = (None,)

    # resolution
    assert "resolution" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["resolution"], tuple), kwargs["resolution"].__class__.__name__
    assert all(
        isinstance(r, tuple) and len(r) == 2 and all(isinstance(s, int) and s > 0 for s in r)
        for r in kwargs["resolution"]
    ), kwargs["resolution"]
    if kwargs["resolution"]:
        prt.print(f"resolution: {', '.join(f'w={w}:h={h}' for h, w in kwargs['resolution'])}")
    else:
        kwargs["resolution"] = (None,)

    # pxl_format
    assert "pxl_format" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["pxl_format"], tuple), kwargs["pxl_format"].__class__.__name__
    assert all(isinstance(p, str) for p in kwargs["pxl_format"]), kwargs["pxl_format"]
    if kwargs["pxl_format"]:
        prt.print(f"pxl_format: {', '.join(kwargs['pxl_format'])}")
    else:
        kwargs["pxl_format"] = (None,)


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
    "--pxl_format",
    type=PixelParamType(),
    multiple=True,
    help="The optional pixel format conversion during encoding.",
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
        If a folder is provided, the database is created inside this folder.
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
    fps : fractions.Fraction, optional
        If provided, the reference video will be resampled on fly just before being encoded.
        This is therefore the frame rate of the transcoded video.
        If this argument is not provided, the frame rate remains unchanged.
    resolution : tuple[int, int], optional
        If provided, the reference video will be reshaped on fly just before being encoded.
        This is therefore the resolution of the transcoded video.
        If this argument is not provided, the resolution remains unchanged.
    pxl_format : str, optional
        If provided, A pixel conversion is performed during encoding.
    """
    with Printer("Parse configuration...") as prt:
        # video
        assert isinstance(videos, tuple), videos.__class__.__name__
        assert videos, "at least one video is required"
        videos = [pathlib.Path(v).expanduser() for v in videos]
        assert all(v.is_file() for v in videos), videos
        prt.print(f"videos    : {', '.join(map(str, videos))}")

        # database
        database = pathlib.Path(database or videos[0].parent / "mendevi.db").expanduser()
        database = database / "mendevi.db" if database.is_dir() else database
        if not database.exists():
            create_database(database)
        prt.print(f"database  : {database}")

        # others
        _parse_args(prt, kwargs)



    # preparation of context
    env_id = add_environement(database)
    keys = ["threads", "effort", "quality", "encoder", "fps", "resolution", "pxl_format"]

    # retrieves the settings for videos that have already been transcoded
    with sqlite3.connect(database) as sql_database:
        sql_database.row_factory = sqlite3.Row
        done: dict[tuple, int] = {}
        for values in sql_database.execute(
            "SELECT * FROM t_enc_encode WHERE enc_env_id=?", (env_id,)
        ):
            values = {
                "effort": values["enc_effort"],
                "encoder": values["enc_encoder"],
                "fps": fractions.Fraction(values["enc_fps"]).limit_denominator(1001),
                "pxl_format": values["enc_pxl_format"],
                "quality": float(values["enc_quality"]),
                "resolution": (values["enc_height"], values["enc_width"]),
                "threads": values["enc_threads"],
                "video_name": values["enc_video_name"],
            }
            values = tuple(values[k] for k in ["video_name", *keys])
            done[values] = done.get(values, 0) + 1

    # iterate on all the parameters
    loops = functools.reduce(operator.mul, [kwargs["repeat"], *(len(kwargs[k]) for k in keys)])
    for i, values in enumerate(
        itertools.product(range(kwargs["repeat"]), videos, *(kwargs[k] for k in keys))
    ):
        values = dict(zip(["repeat", "video", *keys], values), repeat=values[0])
        values["fps"] = values["fps"] or get_rate_video(values["video"])
        values["resolution"] = values["resolution"] or get_resolution(values["video"])
        values["pxl_format"] = values["pxl_format"] or get_pxl_format(values["video"])
        key = (values["video"].name,) + tuple(values[k] for k in keys)
        if done.get(key, 0) > values["repeat"]:
            continue
        with Printer(f"Encode {i}/{loops}...", color="cyan") as prt:
            encode_and_store(database, env_id, values.pop("video"), **{k: values[k] for k in keys})
            done[key] = done.get(key, 0) + 1
            prt.print_time()
