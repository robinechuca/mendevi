"""Perform the video properties measures."""

import pathlib
import random

import click
from context_verbose import Printer

from mendevi.probe import probe_and_store
from mendevi.utils import compute_video_hash

from .parse import parse_videos_database


def _parse_args(prt: Printer, kwargs: dict) -> None:
    """Verification of the arguments."""
    kwargs["ref"] = kwargs.get("ref", ())
    assert isinstance(kwargs["ref"], tuple), kwargs["ref"]
    assert all(isinstance(r, str) for r in kwargs["ref"]), kwargs["ref"]
    kwargs["ref"] = [pathlib.Path(r).expanduser() for r in kwargs["ref"]]
    assert all(r.is_file() for r in kwargs["ref"]), kwargs["ref"]
    if kwargs["ref"]:
        prt.print(f"ref       : {', '.join(r.name for r in kwargs['ref'])}")
    assert "lpips_alex" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["lpips_alex"], bool), kwargs["lpips_alex"].__class__.__name__
    prt.print(f"lpips alex: {'yes' if kwargs['lpips_alex'] else 'no'}")
    assert "lpips_vgg" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["lpips_vgg"], bool), kwargs["lpips_vgg"].__class__.__name__
    prt.print(f"lpips vgg : {'yes' if kwargs['lpips_vgg'] else 'no'}")
    assert "psnr" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["psnr"], bool), kwargs["psnr"].__class__.__name__
    prt.print(f"psnr      : {'yes' if kwargs['psnr'] else 'no'}")
    assert "ssim" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["ssim"], bool), kwargs["ssim"].__class__.__name__
    prt.print(f"ssim      : {'yes' if kwargs['ssim'] else 'no'}")
    assert "rms_sobel" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["rms_sobel"], bool), kwargs["rms_sobel"].__class__.__name__
    prt.print(f"rms sobel : {'yes' if kwargs['rms_sobel'] else 'no'}")
    assert "rms_time_diff" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["rms_time_diff"], bool), kwargs["rms_time_diff"].__class__.__name__
    prt.print(f"rms td    : {'yes' if kwargs['rms_time_diff'] else 'no'}")
    assert "uvq" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["uvq"], bool), kwargs["uvq"].__class__.__name__
    prt.print(f"uvq       : {'yes' if kwargs['uvq'] else 'no'}")
    assert "vmaf" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["vmaf"], bool), kwargs["vmaf"].__class__.__name__
    prt.print(f"vmaf      : {'yes' if kwargs['vmaf'] else 'no'}")


@click.command()
@click.argument("videos", nargs=-1, type=click.Path())
@click.option("-d", "--database", type=click.Path(), help="The database path.")
@click.option(
    "-r", "--ref",
    type=click.Path(),
    multiple=True,
    help="The reference video for comparative metrics.",
)
@click.option("--lpips-alex/--no-lpips-alex", default=False, help="Compute the LPIPS-ALEX or not.")
@click.option("--lpips-vgg/--no-lpips-vgg", default=False, help="Compute the LPIPS-VGG or not.")
@click.option("--psnr/--no-psnr", default=True, help="Compute the PSNR or not.")
@click.option("--ssim/--no-ssim", default=True, help="Compute the SSIM or not.")
@click.option("--rms-sobel/--no-rms-sobel", default=True, help="Compute the C_sob or not.")
@click.option("--rms-time-diff/--no-rms-time-diff", default=True, help="Compute the C_td or not.")
@click.option("--uvq/--no-uvq", default=False, help="Compute the UVQ or not.")
@click.option("--vmaf/--no-vmaf", default=True, help="Compute the VMAF or not.")
def main(videos: tuple[str], database: str | None = None, **kwargs: dict) -> None:
    """Measure the video properties.

    \b
    Parameters
    ----------
    videos : tuple[pathlike], optional
        All videos to be analysed. It can be a glob expression, a directory or a file path.
    database : pathlike, optional
        The path to the database where all measurements are stored.
        If a folder is provided, the database is created inside this folder.
    **kwargs: dict
        Please refer to the detailed arguments below.
    ref : tuple(pathlike), optional
        If provided, in addition to the original video ``o``,
        which has been transcoded to produce video ``x``,
        the metrics will also be calculated in relation to these reference videos ``ref``.
        Finaly comparatives metrics will be between ``o`` and ``x``, and also ``ref`` and ``x``.
    lpips_alex, lpips_vgg, psnr, ssim, vmaf : boolean
        If True, compute the comparative video metric, otherwise, skip it.
    rms_sobel, rms_time_diff, uvq : boolean
        If True, compute the absolute uvq metric, overwise, skip it.

    """
    with Printer("Parse configuration...") as prt:
        videos, database = parse_videos_database(prt, videos, database)
        _parse_args(prt, kwargs)

    kwargs["ref"]: dict[pathlib.Path, bytes] = compute_video_hash(kwargs["ref"])

    # do the job
    random.shuffle(videos)  # heuristic to improve efficiency of multiple acces
    for i, video in enumerate(sorted(kwargs["ref"]) + videos):
        with Printer(f"Probe {i+1}/{len(videos)+len(kwargs['ref'])}...", color="cyan") as prt:
            probe_and_store(database, video, **kwargs)
            prt.print_time()
