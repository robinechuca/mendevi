#!/usr/bin/env python3

"""Perform decoding measures."""

import hashlib
import pathlib
import sqlite3

from context_verbose import Printer
import click

from mendevi.database.complete import add_environement
from mendevi.decode import decode_and_store
from mendevi.utils import unfold_video_files
from .parse import ResolutionParamType



def _parse_args(prt: Printer, kwargs: dict):
    """Verification of the arguments."""
    # repeat
    assert "repeat" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["repeat"], int), kwargs["repeat"].__class__.__name__
    assert kwargs["repeat"] >= 1, kwargs["repeat"]
    prt.print(f"repeat: {kwargs['repeat']}")

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


@click.command()
@click.argument("videos", nargs=-1, type=click.Path())
@click.option("-d", "--database", type=click.Path(), required=True, help="The database path.")
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
    help="The optional video shape conversion during encoding.",
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
        The number of times the experiment is repeated on this environement.
        This allows us to estimate the variance of measurements.
    resolution : tuple[int, int], optional
        If provided, the reference video will be reshaped on fly.
        If this argument is not provided, the resolution remains unchanged.
    """
    with Printer("Parse configuration...") as prt:
        # videos
        videos = set(unfold_video_files(videos))
        prt.print(f"videos: {', '.join(map(str, videos))}")

        # database
        database = pathlib.Path(database or videos[0].parent / "mendevi.db").expanduser()
        database = database / "mendevi.db" if database.is_dir() else database
        if not database.exists():
            create_database(database)
        prt.print(f"database  : {database}")

        # others
        _parse_args(prt, kwargs)

    # preparation of context
    with Printer("Get context and video checksum...") as prt:
        env_id = add_environement(database)
        kwargs["src_vid_id"]: dict[pathlib.Path, str] = {}
        for video in videos:
            with open(video, "rb") as raw:
                kwargs["src_vid_id"][video] = hashlib.file_digest(raw, "md5").hexdigest()
            prt.print(f"{video.name} -> {kwargs["src_vid_id"][video]}")

    # get the full video list
    with sqlite3.connect(database) as sql_database:
        for (vid_id, vid_name) in sql_database.execute("SELECT vid_id, vid_name FROM t_vid_video"):
            print(vid_id, vid_name)

    raise NotImplementedError
    decode_and_store(video)
