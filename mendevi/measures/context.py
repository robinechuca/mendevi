"""Get the information of the environment."""

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
    >>> from mendevi.measures.context import get_ffmpeg_version
    >>> pprint.pprint(get_ffmpeg_version())  # doctest: +ELLIPSIS
    ('ffmpeg version ... Copyright (c) '
     '... the FFmpeg developers\n'
     'built with gcc ...\n'
     'configuration: --prefix=.../ffmpeg_build '
     '--pkg-config-flags=--static '
     '--extra-cflags=-I/home/rrichard/ffmpeg_build/include '
     "--extra-ldflags=-L/home/rrichard/ffmpeg_build/lib --extra-libs='-lpthread "
     "-lm' --ld=g++ --bindir=/home/rrichard/bin --enable-chromaprint "
     '--enable-frei0r --enable-gpl --enable-ladspa --enable-libaom --enable-libass '
     '--enable-libbluray --enable-libbs2b --enable-libcaca --enable-libcdio '
     '--enable-libdav1d --enable-libdrm --enable-libfdk-aac --enable-libflite '
     '--enable-libfontconfig --enable-libfreetype --enable-libfribidi '
     '--enable-libgme --enable-libgsm --enable-libharfbuzz --enable-libmp3lame '
     '--enable-libopenmpt --enable-libopus --enable-libpulse --enable-librav1e '
     '--enable-librubberband --enable-librubberband --enable-libshine '
     '--enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libsvtav1 '
     '--enable-libtheora --enable-libtwolame --enable-libvidstab '
     '--enable-libvo-amrwbenc --enable-libvorbis --enable-libvpl --enable-libvpx '
     '--enable-libvvenc --enable-libwebp --enable-libx264 --enable-libx265 '
     '--enable-libxml2 --enable-libxvid --enable-libzimg --enable-libzvbi '
     '--enable-nonfree --enable-opengl --enable-openssl --enable-vaapi '
     '--enable-version3\n'
     'libavutil ...\n'
     'libavcodec ...\n'
     'libavformat ...\n'
     'libavdevice ...\n'
     'libavfilter ...\n'
     'libswscale ...\n'
     'libswresample ...')
    >>>

    """
    out = subprocess.run(
        ["ffmpeg", "-version"], check=False, capture_output=True,
    ).stdout.decode()
    lines = out.split("\n")
    lines = [line for line in lines if line not in {"", "Exiting with exit code 0"}]
    return "\n".join(lines)


def get_libx265_version() -> str:
    """Return the version of the libx265 encoder.

    Examples
    --------
    >>> from mendevi.measures.context import get_libx265_version
    >>> print(get_libx265_version())  # doctest: +ELLIPSIS
    4...
    [Linux][GCC ...][64 bit] 8...
    MMX2 ... AVX2
    >>>

    """
    out = subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "nullsrc", "-frames:v", "1",
            "-c:v", "libx265",
            "-f", "null", "-",
        ],
        check=False, capture_output=True,
    ).stderr.decode()

    # version
    if (match := re.search(r"HEVC encoder version (?P<version>\S+)", out)) is None:
        logging.getLogger(__name__).warning("failed to find the libx265 version")
        version = ""
    else:
        version = match["version"]
    # build
    if (match := re.search(r"build info (?P<build>.+)\n", out)) is None:
        logging.getLogger(__name__).warning("failed to find the libx265 build info")
        build = ""
    else:
        build = match["build"]
    # cpu
    if (match := re.search(r"using cpu capabilities: (?P<cpu>.+)\n", out)) is None:
        logging.getLogger(__name__).warning("failed to find the libx265 build info")
        cpu = ""
    else:
        cpu = match["cpu"]

    return f"{version}\n{build}\n{cpu}"


def get_libvpx_vp9_version() -> str:
    """Return the version of the libvpx-vp9 encoder.

    Examples
    --------
    >>> from mendevi.measures.context import get_libvpx_vp9_version
    >>> print(get_libvpx_vp9_version())  # doctest: +ELLIPSIS
    v...
    >>>

    """
    out = subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "nullsrc", "-frames:v", "1",
            "-c:v", "libvpx-vp9",
            "-f", "null", "-",
        ],
        check=False, capture_output=True,
    ).stderr.decode()
    if (match := re.search(r"\[libvpx-vp9 @ \w+\] (?P<version>\S+)", out)) is None:
        logging.getLogger(__name__).warning("failed to find the libvpx-vp9 version")
        return ""
    return match["version"]


def get_libsvtav1_version() -> str:
    """Return the version of the libsvtav1 encoder.

    Examples
    --------
    >>> from mendevi.measures.context import get_libsvtav1_version
    >>> print(get_libsvtav1_version())  # doctest: +ELLIPSIS
    ...
    GCC ... 64 bit
    >>>

    """
    out = subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "nullsrc", "-frames:v", "1",
            "-c:v", "libsvtav1",
            "-f", "null", "-",
        ],
        check=False, capture_output=True,
    ).stderr.decode()

    # version
    if (match := re.search(r"SVT-AV1 Encoder Lib (?P<version>\S+)", out)) is None:
        logging.getLogger(__name__).warning("failed to find the libsvtav1 version")
        version = ""
    else:
        version = match["version"]
    # build
    if (match := re.search(r"SVT \[build\]\s*:\s*(?P<build>\S.*\S)\s*\n", out)) is None:
        logging.getLogger(__name__).warning("failed to find the libsvtav1 build info")
        build = ""
    else:
        build = re.sub(r"\s+", " ", match["build"])

    return f"{version}\n{build}"


def get_librav1e_version() -> str:
    """Return the version of the librav1e encoder.

    Examples
    --------
    >>> from mendevi.measures.context import get_librav1e_version
    >>> print(get_librav1e_version())  # doctest: +ELLIPSIS
    rav1e 0.8.0 (...) (release)
    rustc 1.91.1 (...) x86_64-unknown-linux-gnu
    Compiled CPU Features: ...
    Runtime Assembly Support: Enabled
    Runtime Assembly Level: ...
    Threading: Enabled
    Unstable Features: Disabled
    Compiler Flags: -C target-cpu=native
    >>>

    """
    try:
        return subprocess.run(
            ["rav1e", "--version"],
            check=False, capture_output=True,
        ).stdout.decode().strip()
    except FileNotFoundError:
        logging.getLogger(__name__).warning("failed to find the librav1e version")
        return ""


def get_vvc_version() -> str:
    """Return the version of the vvc encoder.

    Examples
    --------
    >>> from mendevi.measures.context import get_vvc_version
    >>> print(get_vvc_version())
    1.13.1
    >>>

    """
    out = subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "nullsrc", "-frames:v", "1",
            "-c:v", "vvc",
            "-f", "null", "-",
        ],
        check=False, capture_output=True,
    ).stderr.decode()
    if (match := re.search(r"libvvenc version: (?P<version>\S+)", out)) is None:
        logging.getLogger(__name__).warning("failed to find the vvc version")
        return ""
    return match["version"]


def get_platform() -> dict:
    """Get basic information about the system.

    Examples
    --------
    >>> import pprint
    >>> from mendevi.measures.context import get_platform
    >>> pprint.pprint(get_platform())  # doctest: +ELLIPSIS
    {'hostname': '...',
     'kernel_version': 'Linux-...',
     'logical_cores': ...,
     'physical_cores': ...,
     'processor': '...',
     'python_compiler': '...',
     'python_version': '...',
     'ram': ...,
     'swap': ...,
     'system_version': '...'}
    >>>

    """
    return {
        "hostname": platform.node(),
        "kernel_version": platform.platform(),
        "logical_cores": psutil.cpu_count(logical=True),
        "physical_cores": psutil.cpu_count(logical=False),
        "processor": platform.processor() or platform.machine(),
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
    >>> from mendevi.measures.context import get_pip_freeze
    >>> print(get_pip_freeze())  # doctest: +ELLIPSIS
    accessible-pygments==...
    ...
    wheel==...
    >>>

    """
    return subprocess.run(
        ["pip", "freeze"], check=False, capture_output=True,
    ).stdout.decode().rstrip()


def get_lshw() -> str:
    """Extract the very accurate exaustive info as big json.

    Examples
    --------
    >>> from mendevi.measures.context import get_lshw
    >>> full_info = get_lshw()
    >>>

    """
    if os.geteuid() != 0:
        logging.getLogger(__name__).warning("you should run as super user to get more system info")
    try:
        out = subprocess.run(
            ["lshw", "-json"], check=False, capture_output=True,
        ).stdout.decode()
    except FileNotFoundError:
        logging.getLogger(__name__).exception("please install lshw: sudo apt install lshw")
    return out


def get_lspci() -> str:
    """Extract the information with lspci -k.

    Examples
    --------
    >>> from mendevi.measures.context import get_lspci
    >>> lspci_info = get_lspci()
    >>>

    """
    try:
        out = subprocess.run(
            ["lspci", "-k"], check=False, capture_output=True,
        ).stdout.decode()
    except FileNotFoundError:
        logging.getLogger(__name__).exception("please install lshw: sudo apt install lshw")
    return out


def full_context() -> dict:
    """Get the full context informations."""
    return {
        "ffmpeg_version": get_ffmpeg_version(),
        "librav1e_version": get_librav1e_version(),
        "libsvtav1_version": get_libsvtav1_version(),
        "libvpx_vp9_version": get_libvpx_vp9_version(),
        "libx265_version": get_libx265_version(),
        "lshw": get_lshw(),
        "lspci": get_lspci(),
        "pip_freeze": get_pip_freeze(),
        "vvc_version": get_vvc_version(),
        **get_platform(),
    }
