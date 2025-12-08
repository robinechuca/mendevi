"""Preprocess step."""

import fractions
import pathlib
import shutil

import click
import cutcutcodec
from context_verbose import Printer

from mendevi.cst import PROFILES
from mendevi.utils import best_profile, get_resolution

from .parse import PixelParamType, ResolutionParamType


def _parse_args(prt: Printer, video: pathlib.Path, kwargs: dict) -> None:
    """Verification of the arguments."""
    # profile
    kwargs["profile"] = kwargs.get("profile")
    if kwargs["profile"] is not None:
        assert isinstance(kwargs["profile"], str), kwargs["profile"].__class__.__name__
        kwargs["profile"] = kwargs["profile"].lower()
        assert kwargs["profile"] in PROFILES, (kwargs["profile"], PROFILES)
    else:  # autodetect profile based on the number of pixels
        kwargs["profile"] = best_profile(*get_resolution(video))
    prt.print(f"profile   : {kwargs['profile']}")

    # fps
    kwargs["fps"] = kwargs.get("fps") or PROFILES[kwargs["profile"]]["fps"]
    assert isinstance(kwargs["fps"], fractions.Fraction), kwargs["fps"].__class__.__name__
    assert kwargs["fps"] > 0, kwargs["fps"]
    prt.print(f"fps       : {kwargs['fps']}")

    # resolution
    kwargs["resolution"] = (
        kwargs.get("resolution") or PROFILES[kwargs["profile"]]["resolution"]
    )
    assert isinstance(kwargs["resolution"], tuple), kwargs["resolution"].__class__.__name__
    assert len(kwargs["resolution"]) == 2, kwargs["resolution"]
    assert all(isinstance(s, int) and s > 0 for s in kwargs["resolution"]), kwargs["resolution"]
    prt.print(f"resolution: h={kwargs['resolution'][0]}:w={kwargs['resolution'][1]}")

    # pix_fmt
    kwargs["pix_fmt"] = kwargs.get("pix_fmt") or PROFILES[kwargs["profile"]]["pix_fmt"]
    assert isinstance(kwargs["pix_fmt"], str), kwargs["pix_fmt"].__class__.__name__
    prt.print(f"pix_fmt   : {kwargs['pix_fmt']}")

    # primaries
    kwargs["primaries"] = (
        kwargs.get("primaries") or PROFILES[kwargs["profile"]]["primaries"]
    )
    assert isinstance(kwargs["primaries"], str), kwargs["primaries"].__class__.__name__
    assert kwargs["primaries"] in cutcutcodec.core.colorspace.cst.PRIMARIES, kwargs["primaries"]
    prt.print(f"primaries : {kwargs['primaries']}")

    # transfer
    kwargs["transfer"] = kwargs.get("transfer") or PROFILES[kwargs["profile"]]["transfer"]
    assert isinstance(kwargs["transfer"], str), kwargs["transfer"].__class__.__name__
    assert kwargs["transfer"] in cutcutcodec.core.colorspace.cst.TRC, kwargs["transfer"]
    prt.print(f"transfer  : {kwargs['transfer']}")

    # range
    kwargs["range"] = kwargs.get("range") or PROFILES[kwargs["profile"]]["range"]
    assert isinstance(kwargs["range"], str), kwargs["range"].__class__.__name__
    assert kwargs["range"] in {"tv", "pc"}, kwargs["range"]
    prt.print(f"range     : {kwargs['range']}")


@click.command()
@click.argument("video", type=click.Path())
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="The destination folder.",
)
@click.option(
    "-p", "--profile",
    type=click.Choice(list(PROFILES)),
    help="The video profile.",
)
@click.option(
    "-f", "--fps",
    type=fractions.Fraction,
    help="The framerate of the reference video.",
)
@click.option(
    "-r", "--resolution",
    type=ResolutionParamType(),
    help="The video resolution.",
)
@click.option(
    "--pix_fmt",
    type=PixelParamType(),
    help="The video pixel format.",
)
@click.option(
    "--primaries",
    type=click.Choice(list(cutcutcodec.core.colorspace.cst.PRIMARIES)),
    help="The colorspace.",
)
@click.option(
     "--transfer",
    type=click.Choice(list(cutcutcodec.core.colorspace.cst.TRC)),
    help="The electro-optical transfer function.",
)
@click.option(
    "--range",
    type=click.Choice(["tv", "pc"]),
    help="The pixel coding range.",
)
def main(video: str, output: str | None = None, **kwargs: dict) -> pathlib.Path:
    """Pre-Process the source video before performing the transcoding measurements.

    This step is required to provide the following guarantees:

    \b
    * Ensure a square pixel ratio.
    * Ensure that you have a lossless encoded video with a codec that allows for fast decoding.
    * Ensure high-quality resizing without spectral aliasing and blur.
    * Ensure the correct management of colour space and associated metadata.
    * Ensure that the appearance of the video is not distorted.
    * Ensure that the pixel format is recognised.

    \b
    Parameters
    ----------
    video : pathlike
        The source video to be prepared.
    output : pathlike, optional
        The destination folder to store the reference file.
        If not provided, it is store in the same folder as the input video.
    **kwargs: dict
        Please refer to the detailed arguments below.
    profile : str, default=autodetect
        A value among ``sd``, ``hd``, ``fhd`` or ``uhd4k``.
        This represents a typical video profile, which includes a pixel format,
        and image resolution, a sampling frequency, and a colour space.
        For more details, see :py:module:`mendevi.cst.profiles`.
        By default, it is automatically detected based on the number of pixels of the video.
    fps : fractions.Fraction, optional
        The default value is defined in the profile.
        The exact frame rate of the video. The video is not encoded with a variable frame rate.
    resolution : tuple[int, int], optional
        The default value is defined in the profile.
        The resolution of the output video. The interpolation is high quality,
        ensuring minimal blurring, no spectral overlap and preservation of proportions.
    pix_fmt : str, optional
        The default value is defined in the profile.
        The pixel format of the video.
    primaries : str, optional
        The default value is defined in the profile.
        The colorspace primaries name of the tristimulus.
        The possible values are those supported by *cutcutcodec.core.colorspace.cst.PRIMARIES*.
    transfer : str, optional
        The default value is defined in the profile.
        The electro-optical transfer function
        that allows you to define the light intensity curve of the pixels.
        The possible values are those supported by *cutcutcodec.core.colorspace.cst.TRC*.
    range : str, optional
        The default value is defined in the profile.
        You can specify ``tv`` for limited range or ``pc`` for full range.

    """
    with Printer("Parse configuration...") as prt:
        # video
        video = pathlib.Path(video).expanduser().resolve()
        assert video.is_file(), video
        prt.print(f"src video : {video}")

        # output
        if output is None:
            output = video.parent
        else:
            output = pathlib.Path(output).expanduser()
            output.mkdir(mode=0o777, parents=True, exist_ok=True)

        # others
        _parse_args(prt, video, kwargs)

        # find filename
        file = []
        for profile, values in PROFILES.items():
            file.append(["reference", video.stem])
            if kwargs["fps"] != values["fps"]:
                file[-1].append(f"{float(kwargs['fps']):.2f}fps")
            if kwargs["resolution"] != values["resolution"]:
                file[-1].append(f"{kwargs['resolution'][1]}x{kwargs['resolution'][0]}")
            if kwargs["pix_fmt"] != values["pix_fmt"]:
                file[-1].append(kwargs["pix_fmt"])
            if kwargs["primaries"] != values["primaries"]:
                file[-1].append(f"p_{kwargs['primaries']}")
            if kwargs["transfer"] != values["transfer"]:
                file[-1].append(f"t_{kwargs['transfer']}")
            if kwargs["range"] != values["range"]:
                file[-1].append(f"r_{kwargs['range']}")
            file[-1].append(profile)
            file[-1] = "_".join(file[-1]) + ".mp4"
        file = {len(f): f for f in file}
        file = file[min(file)]  # select the shortest name
        file = output / file
        prt.print(f"dst video : {file}")

    # write the file
    if not file.exists():
        tmp = file.with_stem(f"{file.stem}_in_process")
        with cutcutcodec.read(video) as container:
            stream = container.out_select("video")[0]
            cutcutcodec.write(
                [stream],
                tmp,
                colorspace=cutcutcodec.Colorspace(
                    "y'pbpr", kwargs["primaries"], kwargs["transfer"],
                ),
                # streams_settings=[{  # extension .mp4
                #     "encodec": "ffv1",  # fast lossless compression
                #     "rate": kwargs["fps"],
                #     "shape": kwargs["resolution"],
                #     "pix_fmt": kwargs["pix_fmt"],
                #     "range": kwargs["range"],
                # }],

                # https://trac.ffmpeg.org/wiki/Encode/H.264
                streams_settings=[{  # extension .mp4
                    "encodec": "libx264",
                    "options": {"preset": "veryfast", "tune": "fastdecode", "qp": "0"},
                    "rate": kwargs["fps"],
                    "shape": kwargs["resolution"],
                    "pix_fmt": kwargs["pix_fmt"],
                    "range": kwargs["range"],
                }],

                # # https://trac.ffmpeg.org/wiki/Encode/AV1#CRF
                # streams_settings=[{  # extension .mp4
                #     "encodec": "libsvtav1",
                #     "options": {"preset": "4", "svtav1-params": "lossless=1"},
                #     "rate": kwargs["fps"],
                #     "shape": kwargs["resolution"],
                #     "pix_fmt": kwargs["pix_fmt"],
                #     "range": kwargs["range"],
                # }],

                # # https://trac.ffmpeg.org/wiki/Encode/AV1#Losslessencoding
                # streams_settings=[{  # extension .mp4
                #     "encodec": "libaom-av1",
                #     "options": {"crf": "0"},
                #     "rate": kwargs["fps"],
                #     "shape": kwargs["resolution"],
                #     "pix_fmt": kwargs["pix_fmt"],
                #     "range": kwargs["range"],
                # }],

            )
        shutil.move(tmp, file)
        file.chmod(0o777)
    return file
