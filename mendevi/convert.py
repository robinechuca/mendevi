#!/usr/bin/env python3

"""Get ffmpeg filter chain command."""

import fractions
import pathlib
import re

import cutcutcodec


def get_convert_cmd(
    video: pathlib.Path | str,
    fps: fractions.Fraction | None,
    pxl_format: str | None,
    resolution: tuple[int, int] | None,
) -> str:
    """Generates the ffmpeg filter command that performs this conversion.

    Parameters
    ----------
    video : pathlike
        The video to be filtered.
        It is required to know the relevant filters and find the best possible order.
    fps : fractions.Fraction, optional
        The new framerate.
    pxl_format : str, optional
        The new pixel format, it has to match the regex ``yuv4[24][024]p(?:10le|12le)?``.
    resolution : tuple[int, int], optional
        The new (heigh, width) video shape.

    Returns
    -------
    filter : str
        The ffmpeg video filter argument. It can be an empty string if nothing has to be done.

    Examples
    --------
    >>> from fractions import Fraction
    >>> import cutcutcodec
    >>> from mendevi.convert import get_convert_cmd
    >>> media = cutcutcodec.utils.get_project_root().parent / "media" / "video" / "intro.webm"
    >>> get_convert_cmd(media, fps=None, pxl_format=None, resolution=None)
    ''
    >>> get_convert_cmd(media, fps=Fraction(60000, 1001), pxl_format="yuv420p10le", resolution=(1080, 1920))
    'scale=h=1080:w=1920:sws_flags=bicubic,format=yuv420p10le,fps=60000/1001'
    >>> get_convert_cmd(media, fps=Fraction(24000, 1001), pxl_format="yuv420p", resolution=(480, 720))
    'fps=24000/1001,scale=h=480:w=720:sws_flags=bicubic'
    >>>
    """
    if fps is not None:
        assert isinstance(fps, fractions.Fraction), fps.__class__.__name__
        assert fps > 0, fps
    if pxl_format is not None:
        assert isinstance(pxl_format, str), pxl_format.__class__.__name__
        assert re.fullmatch(r"yuv4[24][024]p(?:10le|12le)?", pxl_format), pxl_format
    if resolution is not None:
        assert isinstance(resolution, tuple), resolution.__class__.__name__
        assert len(resolution) == 2, resolution
        assert isinstance(resolution[0], int) and isinstance(resolution[1], int), resolution
        assert (resolution[0], resolution[1]) > (0, 0), resolution

    filters: list[str] = []

    # scale (the slowest)
    if resolution is not None and (src := cutcutcodec.get_resolution(video)) != resolution:
        filters = [f"scale=h={resolution[0]}:w={resolution[1]}:sws_flags=bicubic"]

    # format (medium)
    if pxl_format is not None and (src := cutcutcodec.get_pxl_format(video)) != pxl_format:
        match = re.search(r"yuv(?P<samp>\d{3})p(?P<bit>\d+)le", src + "8le")
        bit_per_bloc_src = float(match["bit"]) * sum(map(int, match["samp"]))
        match = re.search(r"yuv(?P<samp>\d{3})p(?P<bit>\d+)le", pxl_format + "8le")
        bit_per_bloc_dst = float(match["bit"]) * sum(map(int, match["samp"]))
        if bit_per_bloc_dst < bit_per_bloc_src:
            filters.insert(0, f"format={pxl_format}")
        else:
            filters.append(f"format={pxl_format}")

    # fps (the fastest)
    if fps is not None and (src := cutcutcodec.get_rate_video(video)) != fps:
        if fps < src:
            filters.insert(0, f"fps={fps}")
        else:
            filters.append(f"fps={fps}")

    return ",".join(filters)
