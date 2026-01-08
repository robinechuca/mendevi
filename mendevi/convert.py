"""Get ffmpeg filter chain command."""

import fractions
import pathlib
import re

from mendevi.utils import get_pix_fmt, get_rate_video, get_resolution


def filter_best_order(
    video: pathlib.Path | str,
    additional_filter: str,
    fps: fractions.Fraction | None,
    pix_fmt: str | None,
    resolution: tuple[int, int] | None,
) -> str:
    """Generate the ffmpeg filter command that performs this conversion.

    Parameters
    ----------
    video : pathlike
        The video to be filtered.
        It is required to know the relevant filters and find the best possible order.
    additional_filter : str
        The additional video filter, (can be an empty string).
    fps : fractions.Fraction, optional
        The new framerate.
    pix_fmt : str, optional
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
    >>> from mendevi.convert import filter_best_order
    >>> media = cutcutcodec.utils.get_project_root() / "media" / "video" / "intro.webm"
    >>> filter_best_order(media, additional_filter="", fps=None, pix_fmt=None, resolution=None)
    ''
    >>> filter_best_order(
    ...     media,
    ...     additional_filter="",
    ...     fps=Fraction(60000, 1001),
    ...     pix_fmt="yuv420p10le",
    ...     resolution=(1080, 1920),
    ... )
    'scale=h=1080:w=1920:sws_flags=bicubic,format=yuv420p10le,fps=60000/1001'
    >>> filter_best_order(
    ...     media,
    ...     additional_filter="",
    ...     fps=Fraction(24000, 1001),
    ...     pix_fmt="yuv420p",
    ...     resolution=(480, 720),
    ... )
    'fps=24000/1001,scale=h=480:w=720:sws_flags=bicubic'
    >>>

    """
    if fps is not None:
        assert isinstance(fps, fractions.Fraction), fps.__class__.__name__
        assert fps > 0, fps
    if pix_fmt is not None:
        assert isinstance(pix_fmt, str), pix_fmt.__class__.__name__
        assert re.fullmatch(r"(?:rgb24)|(?:yuv4[24][024]p)(?:10le|12le)?", pix_fmt), pix_fmt
    if resolution is not None:
        assert isinstance(resolution, tuple), resolution.__class__.__name__
        assert len(resolution) == 2, resolution
        assert isinstance(resolution[0], int), resolution
        assert isinstance(resolution[1], int), resolution
        assert (resolution[0], resolution[1]) > (0, 0), resolution

    filters: list[str] = []

    # scale (the slowest)
    if resolution is not None and (src := get_resolution(video)) != resolution:
        filters = [f"scale=h={resolution[0]}:w={resolution[1]}:sws_flags=bicubic"]

    # format (medium)
    if pix_fmt is not None and (src := get_pix_fmt(video)) != pix_fmt:
        match = re.search(r"yuv(?P<samp>\d{3})p(?P<bit>\d+)le", src + "8le")
        bit_per_bloc_src = (
            96.0 if match is None else float(match["bit"]) * sum(map(int, match["samp"]))
        )
        match = re.search(r"yuv(?P<samp>\d{3})p(?P<bit>\d+)le", pix_fmt + "8le")
        bit_per_bloc_dst = (
            96.0 if match is None else float(match["bit"]) * sum(map(int, match["samp"]))
        )
        if bit_per_bloc_dst < bit_per_bloc_src:
            filters.insert(0, f"format={pix_fmt}")
        else:
            filters.append(f"format={pix_fmt}")

    # fps (the fastest)
    if fps is not None and (src := get_rate_video(video)) != fps:
        if fps < src:
            filters.insert(0, f"fps={fps}")
        else:
            filters.append(f"fps={fps}")

    # additional filter
    if additional_filter:
        filters.insert(0, additional_filter)

    return ",".join(filters)
