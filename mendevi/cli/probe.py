#!/usr/bin/env python3

"""Perform the video properties measures."""

from context_verbose import Printer
import click

from .parse import parse_videos_database



def _parse_args(prt: Printer, kwargs: dict):
    """Verification of the arguments."""
    assert "lpips_alex" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["lpips_alex"], bool), kwargs["lpips_alex"].__class__.__name__
    prt.print(f"lpips alex: {'yes' if kwargs['lpips_alex'] else 'no'}")
    assert "lpips_vgg" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["lpips_vgg"], bool), kwargs["lpips_vgg"].__class__.__name__
    prt.print(f"lpips vgg : {'yes' if kwargs['lpips_vgg'] else 'no'}")
    assert "psnr" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["psnr"], bool), kwargs["psnr"].__class__.__name__
    prt.print(f"lpsnr     : {'yes' if kwargs['psnr'] else 'no'}")
    assert "ssim" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["ssim"], bool), kwargs["ssim"].__class__.__name__
    prt.print(f"ssim      : {'yes' if kwargs['ssim'] else 'no'}")
    assert "uvq" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["uvq"], bool), kwargs["uvq"].__class__.__name__
    prt.print(f"uvq       : {'yes' if kwargs['uvq'] else 'no'}")
    assert "vmaf" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["vmaf"], bool), kwargs["vmaf"].__class__.__name__
    prt.print(f"vmaf      : {'yes' if kwargs['vmaf'] else 'no'}")


@click.command()
@click.argument("videos", nargs=-1, type=click.Path())
@click.option("-d", "--database", type=click.Path(), help="The database path.")
@click.option("--lpips-alex/--no-lpsis-alex", default=True, help="Compute the LPIPS-ALEX or not.")
@click.option("--lpips-vgg/--no-lpsis-vgg", default=True, help="Compute the LPIPS-VGG or not.")
@click.option("--psnr/--no-psnr", default=True, help="Compute the PSNR or not.")
@click.option("--ssim/--no-ssim", default=True, help="Compute the SSIM or not.")
@click.option("--uvq/--no-uvq", default=True, help="Compute the UVQ or not.")
@click.option("--vmaf/--no-vmaf", default=True, help="Compute the VMAF or not.")
def main(videos: tuple[str], database: str = None, **kwargs):
    """Measures the video properties.

    \b
    Parameters
    ----------
    videos : tuple[pathlike], optional
        All videos to be analysed. It can be a glob expression, a directory or a file path.
    database : pathlike, optional
        The path to the database where all measurements are stored.
        If a folder is provided, the database is created inside this folder.
    """
    with Printer("Parse configuration...") as prt:
        videos, database = parse_videos_database(prt, videos, database)
        _parse_args(prt, kwargs)
