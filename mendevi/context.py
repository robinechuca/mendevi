#!/usr/bin/env python3

"""Get the information of the environement."""

import logging
import os
import platform
import re
import subprocess

import psutil


def get_ffmpeg_version() -> str:
    r"""Return the version of ffmpeg.

    Examples
    --------
    >>> import pprint
    >>> from mendevi.context import get_ffmpeg_version
    >>> pprint.pprint(get_ffmpeg_version())
    ('ffmpeg version N-120220-g934e1c23b0 Copyright (c) 2000-2025 the FFmpeg '
     'developers\n'
     'built with gcc 14 (Ubuntu 14.2.0-4ubuntu2)\n'
     'configuration: --prefix=/home/rrichard/ffmpeg_build '
     '--pkg-config-flags=--static '
     '--extra-cflags=-I/home/rrichard/ffmpeg_build/include '
     "--extra-ldflags=-L/home/rrichard/ffmpeg_build/lib --extra-libs='-lpthread "
     "-lm' --ld=g++ --bindir=/home/rrichard/bin --enable-gpl --enable-gnutls "
     '--enable-libaom --enable-libass --enable-libfdk-aac --enable-libfreetype '
     '--enable-libmp3lame --enable-libopus --enable-libsvtav1 --enable-libdav1d '
     '--enable-libvorbis --enable-libvpx --enable-libx264 --enable-libx265 '
     '--enable-libvvenc --enable-nonfree\n'
     'libavutil      60.  4.101 / 60.  4.101\n'
     'libavcodec     62.  6.100 / 62.  6.100\n'
     'libavformat    62.  1.101 / 62.  1.101\n'
     'libavdevice    62.  0.100 / 62.  0.100\n'
     'libavfilter    11.  1.100 / 11.  1.100\n'
     'libswscale      9.  0.100 /  9.  0.100\n'
     'libswresample   6.  0.100 /  6.  0.100')
    """
    out = subprocess.run(
        ["ffmpeg", "-version"], check=False, capture_output=True
    ).stdout.decode()
    lines = out.split("\n")
    lines = [l for l in lines if l not in {"", "Exiting with exit code 0"}]
    out = "\n".join(lines)
    return out


def get_libx265_version() -> str:
    """Return the version of the libx265 encoder.

    Examples
    --------
    >>> from mendevi.context import get_libx265_version
    >>> print(get_libx265_version())
    4.1+188-cd4f0d6e9
    [Linux][GCC 14.2.0][64 bit] 8bit+10bit+12bit
    MMX2 SSE2Fast LZCNT SSSE3 SSE4.2 AVX FMA3 BMI2 AVX2
    >>>
    """
    out = subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "nullsrc", "-frames:v", "1",
            "-c:v", "libx265",
            "-f", "null", os.devnull,
        ],
        check=False, capture_output=True
    ).stderr.decode()

    # version
    if (match := re.search(r"HEVC encoder version (?P<version>\S+)", out)) is None:
        logging.warning("failed to find the libx265 version")
        version = ""
    else:
        version = match["version"]
    # build
    if (match := re.search(r"build info (?P<build>.+)\n", out)) is None:
        logging.warning("failed to find the libx265 build info")
        build = ""
    else:
        build = match["build"]
    # cpu
    if (match := re.search(r"using cpu capabilities: (?P<cpu>.+)\n", out)) is None:
        logging.warning("failed to find the libx265 build info")
        cpu = ""
    else:
        cpu = match["cpu"]

    out = f"{version}\n{build}\n{cpu}"
    return out


def get_libvpx_vp9_version() -> str:
    """Return the version of the libx265 encoder.

    Examples
    --------
    >>> from mendevi.context import get_libvpx_vp9_version
    >>> print(get_libvpx_vp9_version())
    v1.14.1
    >>>
    """
    out = subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "nullsrc", "-frames:v", "1",
            "-c:v", "libvpx-vp9",
            "-f", "null", os.devnull,
        ],
        check=False, capture_output=True
    ).stderr.decode()
    if (match := re.search(r"\[libvpx-vp9 @ \w+\] (?P<version>\S+)", out)) is None:
        logging.warning("failed to find the libvpx-vp9 version")
        return ""
    return match["version"]


def get_libsvtav1_version() -> str:
    """Return the version of the libx265 encoder.

    Examples
    --------
    >>> from mendevi.context import get_libsvtav1_version
    >>> print(get_libsvtav1_version())
    v3.0.2-103-gc10214fa
    GCC 14.2.0 64 bit
    >>>
    """
    out = subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "nullsrc", "-frames:v", "1",
            "-c:v", "libsvtav1",
            "-f", "null", os.devnull,
        ],
        check=False, capture_output=True
    ).stderr.decode()

    # version
    if (match := re.search(r"SVT-AV1 Encoder Lib (?P<version>\S+)", out)) is None:
        logging.warning("failed to find the libsvtav1 version")
        version = ""
    else:
        version = match["version"]
    # build
    if (match := re.search(r"SVT \[build\]\s*:\s*(?P<build>\S.*\S)\s*\n", out)) is None:
        logging.warning("failed to find the libsvtav1 build info")
        build = ""
    else:
        build = re.sub(r"\s+", " ", match["build"])

    out = f"{version}\n{build}"
    return out


def get_vvc_version() -> str:
    """Return the version of the libx265 encoder.

    Examples
    --------
    >>> from mendevi.context import get_vvc_version
    >>> print(get_vvc_version())
    1.13.1
    >>>
    """
    out = subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "nullsrc", "-frames:v", "1",
            "-c:v", "vvc",
            "-f", "null", os.devnull,
        ],
        check=False, capture_output=True
    ).stderr.decode()
    if (match := re.search(r"libvvenc version: (?P<version>\S+)", out)) is None:
        logging.warning("failed to find the vvc version")
        return ""
    return match["version"]


def get_platform() -> dict:
    """Get basic information about the system.

    Examples
    --------
    >>> import pprint
    >>> from mendevi.context import get_platform
    >>> pprint.pprint(get_platform())
    {'hostname': 'PTB-5CG4414JJD',
     'kernel_version': 'Linux-6.11.0-29-generic-x86_64-with-glibc2.40',
     'processor': 'x86_64',
     'python_compiler': 'x86_64',
     'python_version': 'x86_64',
     'system_version': '#29-Ubuntu SMP PREEMPT_DYNAMIC Fri Jun 13 20:29:41 UTC '
                       '2025'}
    >>>
    """
    return {
        "hostname": platform.node(),
        "kernel_version": platform.platform(),
        "logical_cores": psutil.cpu_count(logical=True),
        "physical_cores": psutil.cpu_count(logical=False),
        "processor": platform.processor(),
        "python_compiler": platform.python_compiler(),
        "python_version": platform.python_version(),
        "ram": psutil.virtual_memory().total,
        "swap": psutil.swap_memory().total,
        "system_version": platform.version(),
    }


def get_pip_freeze() -> str:
    """Return the sorted pip freeze.

    Examples
    --------
    >>> from mendevi.context import get_pip_freeze
    >>> print(get_pip_freeze())
    """
    out = subprocess.run(
        ["pip", "freeze"], check=False, capture_output=True,
    ).stdout.decode()
    return out


def get_lshw() -> str:
    """The very accurate exaustive info as big json.

    Examples
    --------
    >>> from mendevi.context import get_lshw
    >>> full_info = get_lshw()
    >>>
    """
    if os.geteuid() != 0:
        logging.warning("you should run as super user to get more system info")
    try:
        out = subprocess.run(
            ["lshw", "-json"], check=False, capture_output=True,
        ).stdout.decode()
    except FileNotFoundError:
        logging.error("please install lshw: sudo apt install lshw")
    return out


def full_context() -> dict:
    """Get the full context informations."""
    return {
        "ffmpeg_version": get_ffmpeg_version(),
        "libx265_version": get_libx265_version(),
        "libvpx_vp9_version": get_libvpx_vp9_version(),
        "libsvtav1_version": get_libsvtav1_version(),
        "vvc_version": get_vvc_version(),
        "pip_freeze": get_pip_freeze(),
        "lshw": get_lshw(),
        **get_platform()
    }
