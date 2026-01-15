"""Perform decoding measures."""

import hashlib
import inspect
import itertools
import math
import sqlite3
from typing import TYPE_CHECKING

import click
from context_verbose import Printer

from mendevi.database.complete import add_environment
from mendevi.database.meta import merge_extractors
from mendevi.decode import decode_and_store
from mendevi.utils import compute_video_hash, get_resolution

from .parse import CallBackType, CopyRamType, ResolutionParamType, parse_videos_database

if TYPE_CHECKING:
    import pathlib


def _parse_args(prt: Printer, kwargs: dict) -> None:
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
    prt.print(
        f"resolution: {
            ', '.join(f'w={w}:h={h}' for h, w in kwargs['resolution'])
            if kwargs['resolution'] else
            'same as source'
        }",
    )
    kwargs["resolution"] = kwargs["resolution"] or (None,)

    # filter
    kwargs["filter"] = kwargs.get("filter", ())
    assert isinstance(kwargs["filter"], tuple), kwargs["filter"].__class__.__name__
    assert all(isinstance(f, str) for f in kwargs["filter"]), kwargs["filter"]
    prt.print(
        f"filters   : {', '.join(map(str, kwargs['filter'])) if kwargs['filter'] else 'no filter'}",
    )
    kwargs["filter"] =  kwargs["filter"] or (None,)

    # family
    assert isinstance(kwargs["family"], tuple), kwargs["family"].__class__.__name__
    assert all(isinstance(p, str) for p in kwargs["family"]), kwargs["family"]
    assert all(p in {"cpu", "cuvid"} for p in kwargs["family"]), kwargs["family"]
    prt.print(f"dec type  : {', '.join(kwargs['family'])}")

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
@click.option(
    "--family",
    type=click.Choice(["cpu", "cuvid"]),
    default=["cpu"],
    multiple=True,
    help="The family of decoders.",
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
def main(videos: tuple[str], database: str | None = None, **kwargs: dict) -> None:
    """Measures activity during decoding.

    \b
    Parameters
    ----------
    videos : tuple[pathlike], optional
        All videos to be decoded. It can be a glob expression, a directory or a file path.
    database : pathlike, optional
        The path to the database where all measurements are stored.
        If a folder is provided, the database is created inside this folder.
    **kwargs: dict
        Please refer to the detailed arguments below.
    repeat : int, default=5
        The number of times the experiment is repeated on this environment.
        This allows us to estimate the variance of measurements.
    resolution : tuple[int, int], optional
        If provided, the decoded video will be reshaped on fly.
        If this argument is not provided, the resolution remains unchanged.
    filter : str, optional
        The additional ffmpeg video filter (after the -vf command)
        to be applied immediately after decoding and before other conversions.
    family : tuple[str], default=("cpu",)
        The nature of the decoder.
        "cpu" is always working, and "cuvid" requires compatible nvidia gpu.
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
        _parse_args(prt, kwargs)

    # preparation of context
    env_id = add_environment(database)
    kwargs["dec_vid_id"]: dict[pathlib.Path, bytes] = compute_video_hash(videos)

    # retrieves the settings for videos that have already been decoded
    _, family_extractor = merge_extractors({"decoder_family"}, return_callable=True)
    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        done: dict[tuple, int] = {}
        for row in conn.execute(
            "SELECT * FROM t_dec_decode WHERE dec_env_id=?", (env_id,),
        ):
            values = (
                row["dec_vid_id"],
                row["dec_filter"] or "",
                (row["dec_height"], row["dec_width"]),
                family_extractor({"dec_decoder": row["dec_decoder"]})["decoder_family"],
            )
            done[values] = done.get(values, 0) + 1
        prt.print(f"{sum(done.values())} video already decoded under these environment")

    # iterate on all the parameters
    loops = sorted(
        itertools.product(videos, kwargs["filter"], kwargs["resolution"], kwargs["family"]),
        key=lambda t: hashlib.md5(str(t).encode("utf-8")).hexdigest(),  # repetable shuffle
    )
    for i, (repeat, values_) in enumerate(itertools.product(range(kwargs["repeat"]), loops)):
        values = dict(zip(("video", "filter", "resolution", "family"), values_, strict=True))
        values["repeat"] = repeat
        values["dec_vid_id"] = kwargs["dec_vid_id"][values["video"]]
        values["filter"] = values["filter"] or ""
        values["resolution"] = values["resolution"] or get_resolution(values["video"])
        values["callback"] = kwargs["callback"]
        key = (values["dec_vid_id"], values["filter"], values["resolution"], values["family"])
        if done.get(key, 0) > values["repeat"]:
            continue
        with Printer(f"Decode {i+1}/{kwargs["repeat"]*len(loops)}...", color="cyan") as prt:
            decode_and_store(database, env_id, values.pop("video"), ram=kwargs["ram"], **values)
            done[key] = done.get(key, 0) + 1
            prt.print_time()
