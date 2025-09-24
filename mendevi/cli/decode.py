#!/usr/bin/env python3

"""Perform decoding measures."""

import itertools
import pathlib
import sqlite3

from context_verbose import Printer
import click

from mendevi.database.complete import add_environment
from mendevi.decode import decode_and_store
from mendevi.utils import compute_video_hash, get_resolution
from .parse import ResolutionParamType, parse_videos_database



def _parse_args(prt: Printer, kwargs: dict):
    """Verification of the arguments."""
    # repeat
    assert "repeat" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["repeat"], int), kwargs["repeat"].__class__.__name__
    assert kwargs["repeat"] >= 1, kwargs["repeat"]
    prt.print(f"repeat    : {kwargs['repeat']}")

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

        # filter
    kwargs["filter"] = kwargs.get("filter", ())
    assert isinstance(kwargs["filter"], tuple), kwargs["filter"].__class__.__name__
    assert all(isinstance(f, str) for f in kwargs["filter"]), kwargs["filter"]
    if kwargs["filter"]:
        prt.print(f"filters   : {', '.join(map(str, kwargs['filter']))}")
    else:
        kwargs["filter"] = ("",)


@click.command()
@click.argument("videos", nargs=-1, type=click.Path())
@click.option("-d", "--database", type=click.Path(), help="The database path.")
@click.option(
    "-r", "--repeat",
    type=int,
    default=5,
    help="The number of times the decoding is repeated on this machine.",
)
@click.option(
    "--resolution",
    type=ResolutionParamType(),
    multiple=True,
    help="The optional video shape conversion during decoding.",
)
@click.option(
    "--filter",
    type=str,
    multiple=True,
    help="The ffmpeg filter to apply on fly.",
)
def main(videos: tuple[str], database: str = None, **kwargs):
    """Measures activity during decoding.

    \b
    Parameters
    ----------
    videos : tuple[pathlike], optional
        All videos to be decoded. It can be a glob expression, a directory or a file path.
    database : pathlike, optional
        The path to the database where all measurements are stored.
        If a folder is provided, the database is created inside this folder.
    repeat : int, default=5
        The number of times the experiment is repeated on this environment.
        This allows us to estimate the variance of measurements.
    resolution : tuple[int, int], optional
        If provided, the decoded video will be reshaped on fly.
        If this argument is not provided, the resolution remains unchanged.
    filter : str, optional
        The additional ffmpeg video filter (after the -vf command)
        to be applied immediately after decoding and before other conversions.
    """
    with Printer("Parse configuration...") as prt:
        videos, database = parse_videos_database(prt, videos, database)
        _parse_args(prt, kwargs)

    # preparation of context
    env_id = add_environment(database)
    kwargs["dec_vid_id"]: dict[pathlib.Path, bytes] = compute_video_hash(videos)

    # retrieves the settings for videos that have already been decoded
    with sqlite3.connect(database) as sql_database:
        sql_database.row_factory = sqlite3.Row
        done: dict[tuple, int] = {}
        for values in sql_database.execute(
            "SELECT * FROM t_dec_decode WHERE dec_env_id=?", (env_id,)
        ):
            values = (
                values["dec_vid_id"],
                values["dec_filter"],
                (values["dec_height"], values["dec_width"]),
            )
            done[values] = done.get(values, 0) + 1

    # iterate on all the parameters
    loops = kwargs["repeat"] * len(videos) * len(kwargs["filter"]) * len(kwargs["resolution"])
    for i, values in enumerate(
        itertools.product(range(kwargs["repeat"]), videos, kwargs["filter"], kwargs["resolution"])
    ):
        values = dict(zip(("repeat", "video", "filter", "resolution"), values))
        values["dec_vid_id"] = kwargs["dec_vid_id"][values["video"]]
        values["filter"] = values["filter"] or ""
        values["resolution"] = values["resolution"] or get_resolution(values["video"])
        key = (values["dec_vid_id"], values["resolution"])
        if done.get(key, 0) > values["repeat"]:
            continue
        with Printer(f"Decode {i+1}/{loops}...", color="cyan") as prt:
            decode_and_store(database, env_id, values.pop("video"), **values)
            done[key] = done.get(key, 0) + 1
            prt.print_time()
