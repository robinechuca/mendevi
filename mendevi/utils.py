#!/usr/bin/env python3

"""Provide simple tools."""

import base64
import functools
import gzip
import logging
import pathlib
import platform
import subprocess
import typing

from cutcutcodec.core.io import VIDEO_SUFFIXES
import av
import unidecode


@functools.cache
def get_context() -> str:
    """Return the base64 zipped context."""
    # echo stdout | gzip -c - | base64 -w0 | base64 --decode | gunzip -c -
    unfold = "echo %s | base64 --decode | gunzip -c -"
    return {
        "hostnamectl": unidecode.unidecode(
            subprocess.run(["hostnamectl"], check=False, capture_output=True).stdout
            .decode("utf-8")
        ),
        "base64_gzip_ffmpeg": unfold % base64.b64encode(gzip.compress(subprocess.run(
            ["ffmpeg", "-version"], check=False, capture_output=True,
        ).stdout)).decode(),
        "base64_gzip_lshw": unfold % base64.b64encode(gzip.compress(subprocess.run(
            ["lshw"], check=False, capture_output=True,  # sudo apt install lshw
        ).stdout)).decode(),
        "hostname": platform.node(),
        "base64_gzip_pipfreeze": unfold % base64.b64encode(gzip.compress(subprocess.run(
            ["pip", "freeze"], check=False, capture_output=True,
        ).stdout)).decode(),
        "pyav": av.library_versions,
    }


def unfold_video_files(
    paths: typing.Iterable[str | bytes | pathlib.Path]
) -> typing.Iterable[pathlib.Path]:
    """Explore recursively the folders to find the video path.

    Parameters
    ----------
    paths : list[pathlike]
        All the folders, files, glob or recursive glob expression.

    Yields
    ------
    filename : pathlib.Path
        The full path of the image.
    """
    assert hasattr(paths, "__iter__"), paths.__class__.__name__
    for path in paths:
        path = pathlib.Path(path).expanduser().resolve()
        if path.is_file():
            yield path
        elif path.is_dir():
            for root, _, files in path.walk():
                for file in files:
                    file = root / file
                    if file.suffix.lower() in VIDEO_SUFFIXES:
                        yield file
        elif "*" in path.name and path.parent.is_dir():
            yield from unfold_video_files(path.parent.glob(path.name))
        elif "**" in (parts := path.parts):
            idx = parts.index("**")
            yield from unfold_video_files(
                pathlib.Path(*parts[:idx]).glob(pathlib.Path(*parts[idx:]))
            )
        else:
            logging.warning("the path %s is not correct", path)
