"""Parse and verify some user input."""

import importlib
import inspect
import math
import pathlib
import re
import typing

import click
import context_verbose
import Levenshtein
from context_verbose import Printer

from mendevi.cst.labels import LABELS
from mendevi.database.create import create_database, is_sqlite
from mendevi.database.meta import extract_names
from mendevi.utils import unfold_video_files


class CallBackType(click.ParamType):
    """Parse the callback function."""

    name = "callback"

    def convert(self, value: str, param: click.Option, ctx: click.Context) -> typing.Callable:
        """Normalize pixel format."""
        # extract clues
        if (func_name := re.search(r"\.py\?(?P<func>[a-zA-Z_]\w*)$", value)) is not None:
            func_name = func_name["func"]
            value = value[:-len(func_name)-1]
        path = pathlib.Path(value)
        if not path.exists():
            self.fail(f"{path!r} does not exists", param, ctx)

        # import the user file
        spec = importlib.util.spec_from_file_location(path.stem, path)
        modulevar = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulevar)

        # find the function
        funcs = dict(inspect.getmembers(modulevar, inspect.isfunction))
        if func_name is None:
            if len(funcs) != 1:
                self.fail(
                    f"please specifiy the function to use {', '.join(sorted(funcs))}", param, ctx,
                )
            func_name = next(iter(funcs))
        if func_name not in funcs:
            self.fail(
                f"the func name {func_name!r} is not in {', '.join(sorted(funcs))}", param, ctx,
            )
        return funcs[func_name]


class CopyRamType(click.ParamType):
    """Parse the ram copy format."""

    name = "ram"

    def convert(self, value: str | float, param: click.Option, ctx: click.Context) -> float:
        """Normalize pixel format."""
        if isinstance(value, str):
            value = value.lower()
            if (converted := {"yes": 0.0, "no": math.inf}.get(value)) is not None:
                return converted
            try:
                value = float(value)
            except ValueError as err:
                self.fail(err, param, ctx)
        if not isinstance(value, float):
            self.fail(f"{value!r} has to be float", param, ctx)
        if value < 0.0:
            self.fail(f"{value!r} is not positive", param, ctx)
        return value


class PixelParamType(click.ParamType):
    """Parse the pixel format."""

    name = "pixel"

    def convert(self, value: str, param: click.Option, ctx: click.Context) -> str:
        """Normalize pixel format."""
        value = value.lower()
        if not re.fullmatch(r"yuv4[24][024]p(?:10le|12le)?", value):
            self.fail(f"{value!r} is not a valid pixel format", param, ctx)
        return value


class ResolutionParamType(click.ParamType):
    """Parse the resolution."""

    name = "resolution"

    def convert(self, value: str, param: click.Option, ctx: click.Context) -> tuple[int, int]:
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
        msg = f"only one database must be provided, {candidates} are given"
        raise ValueError(msg)
    for file_ in files:
        file = pathlib.Path(file_) / "mendevi.db"
        if is_sqlite(file):
            candidates.add(str(file))
    if len(candidates) == 1:
        return candidates.pop()
    return None


def parse_expr(expr: str | None, prt: Printer, start_msg: str) -> None:
    """Ensure that the expression provided is valid."""
    if expr is None:
        return
    assert isinstance(expr, str), expr.__class__.__name__
    variables = extract_names(expr)  # retrieves the names of variables in the expression
    if excess := variables - set(LABELS):
        def dist(label: list[str], excess: set[str]) -> tuple[int, str]:
            return (
                min(Levenshtein.distance(label, e) for e in excess),
                label,
            )
        msg = (
            f"{', '.join(sorted(excess))} are not recognized variables.\n"
            f"Do you mean {', '.join(sorted(LABELS, key=lambda lab: dist(lab, excess)))}?"
        )
        raise ValueError(msg)
    prt.print(f"{start_msg}: {expr}")


def parse_videos_database(
    prt: context_verbose.Printer,
    videos: tuple[str],
    database: str | None = None,
    *,
    _quiet: bool = False,
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
                msg = "please provide the database path"
                raise ValueError(msg)
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
