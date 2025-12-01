"""Test if the dependents libraries are well installed and linked.

Basicaly, it checks if the installation seems to be correct.
"""

import logging
import re
import subprocess

import av
import torch

VERSION_MIN = 6
VERSION_MAX = 8


def test_av_ffmpeg_link() -> None:
    """Test the pyav and ffmpeg dependencies."""
    try:
        version_ffmpeg = (
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True).stdout.decode()
        )
    except subprocess.CalledProcessError as err:
        msg = (
            "ffmpeg is not accessible from the 'ffmpeg' commande line, "
            "please refer to the ffmpeg installation guide"
        )
        raise ImportError(
            msg,
        ) from err
    try:
        version_ffprobe = (
            subprocess.run(["ffprobe", "-version"], capture_output=True, check=True).stdout.decode()
        )
    except subprocess.CalledProcessError as err:
        msg = (
            "ffprobe is not accessible from the 'ffprobe' but ffmpeg is installed, "
            "please check your environement variables"
        )
        raise ImportError(
            msg,
        ) from err

    version_pattern = r"version\s+[^\n]*?(?P<major>\d+)\.(?P<minor>\d+)"
    if (version := re.search(version_pattern, version_ffmpeg)) is None:
        msg = "failed to decode the version of ffmpeg"
        raise RuntimeError(msg)
    assert VERSION_MIN <= int(version["major"]) <= VERSION_MAX, (
        "only the version 4, 5, and 6 of ffmpeg are supported, "
        f"not {version['major']}.{version['minor']}"
    )
    if (version := re.search(version_pattern, version_ffprobe)) is None:
        msg = "failed to decode the version of ffprobe"
        raise RuntimeError(msg)
    assert VERSION_MIN <= int(version["major"]) <= VERSION_MAX, (
        "only the version 4, 5, and 6 of ffprobe are supported, "
        f"not {version['major']}.{version['minor']}"
    )

    version_pattern = r"(?P<major>\d+)\.\s*(?P<minor>\d+)\.\s*(?P<micro>\d+)"
    for lib, (major, minor, micro) in av.library_versions.items():
        if (version := re.search(rf"{lib}\s+{version_pattern}", version_ffmpeg)) is None:
            msg = f"failed to extract the ffmpeg {lib} version"
            raise RuntimeError(msg)
        if (
            (major, minor, micro)
            != (int(version["major"]), int(version["minor"]), int(version["micro"]))
        ):
            logging.getLogger(__name__).warning(
                "the av version of %s is %d.%d.%d but %s.%s.%s for ffmpeg, "
                "please reinstall pyav using option --no-binary, see the installation guide "
                "https://pyav.org/docs/develop/overview/installation.html",
                lib, major, minor, micro, version["major"], version["minor"], version["micro"],
            )


def test_gpu_torch() -> None:
    """Test if torch is able to use the GPU."""
    # possible to test lspci | grep ' NVIDIA '
    if torch.cuda.is_available():
        return  # case always ok
    try:
        result = subprocess.run(["lshw", "-C", "display"], capture_output=True, check=True)
    except FileNotFoundError as err:
        try:
            subprocess.run(["nvidia-smi"], capture_output=True, check=True)
        except FileNotFoundError:
            return  # assume there are not graphical card
        msg = (
            "There seems to be an nvidia gpu on this machine, "
            "however torch is not able to use it, please reinstall cuda"
        )
        raise ImportError(msg) from err
    if b" nvidia " in result.stdout.lower():
        msg = (
            "There seems to be an nvidia gpu on this machine, "
            "however torch is not able to use it, please reinstall cuda"
        )
        raise ImportError(msg)
