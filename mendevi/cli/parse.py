#!/usr/bin/env python3

"""Parse and verify some user input."""

import pathlib
import re

import click
import context_verbose

from mendevi.database.create import create_database, is_sqlite
from mendevi.utils import unfold_video_files


class PixelParamType(click.ParamType):
    """Parse the pixel format."""

    name = "pixel"

    def convert(self, value, param, ctx):
        """Normalize pixel format."""
        value = value.lower()
        if not re.fullmatch(r"yuv4[24][024]p(?:10le|12le)?", value):
            self.fail(f"{value!r} is not a valid pixel format", param, ctx)
        return value


class ResolutionParamType(click.ParamType):
    """Parse the resolution."""

    name = "resolution"

    def convert(self, value, param, ctx):
        """Convert a video resolution into tuple."""
        if (match := re.search(
            r"(?P<t1>he)?\D*(?P<d1>\d+)\D+?(?P<t2>w)?\D*(?P<d2>\d+)", value.lower(),
        )) is None:
            self.fail(f"{value!r} is not a valid video shape", param, ctx)
        if match["t1"] == "he" or match["t2"] == "w":
            return (int(match["d1"]), int(match["d2"]))
        return (int(match["d2"]), int(match["d1"]))


def _guess_database(files: tuple[str]) -> str | None:
    """Try to find if one of the file is a database file."""
    candidates: set[str] = set()
    for file in files:
        if is_sqlite(file):
            candidates.add(file)
    if len(candidates) == 1:
        return candidates.pop()
    if len(candidates) > 1:
        raise ValueError(f"only one database must be provided, {candidates} are given")
    for file in files:
        file = pathlib.Path(file) / "mendevi.db"
        if is_sqlite(file):
            candidates.add(str(file))
    if len(candidates) == 1:
        return candidates.pop()
    return None


def parse_videos_database(
    prt: context_verbose.Printer, videos: tuple[str], database: str = None, _quiet: bool = False,
) -> tuple[list[pathlib.Path], pathlib.Path]:
    """Find or create the database and extract all the videos.

    Parameters
    ----------
    prt : context_verbose.Printer
        The Printer instance to verbose the process.
    videos : tuple[str]
        The full pseudo pathlike video pointers.
    database : str, optional
        The provided link to the video.

    Returns
    -------
    videos : list[pathlib.Path]
        All the existing unfolded video files.
    database : pathlib.Path
        The existing database path.

    """
    # test if database is provided
    assert isinstance(videos, tuple), videos.__class__.__name__
    assert all(isinstance(v, str) for v in videos), videos
    database = database or _guess_database(videos)

    # videos
    videos = list(unfold_video_files(videos))
    if len(videos) == 1 and not _quiet:
        prt.print(f"video     : {videos[0]}")
    elif len(videos) > 1 and not _quiet:
        prt.print(f"videos    : {len(videos)} files founded")

    # database
    if not database:
        database_candidates = {v.parent for v in videos}
        database_candidates = {f / "mendevi.db" for f in database_candidates}
        if not (database := sorted({d for d in database_candidates if d.is_file()})):
            if len(database_candidates) != 1:  # if no ambiguity, we can create it
                raise ValueError("please provide the database path")
            database = database_candidates
        database = database.pop()
    else:
        database = pathlib.Path(database).expanduser()
        database = database / "mendevi.db" if database.is_dir() else database
    if not database.exists():
        create_database(database)
        if not _quiet:
            prt.print(f"database  : {database} (just created)")
    elif not _quiet:
        prt.print(f"database  : {database}")

    return videos, database
