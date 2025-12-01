"""Test the ffmpeg encoding command on a stupid example."""

import itertools
import shlex
import subprocess

from mendevi.ffmpeg_cmd import (
    _encode_av1_nvenc,
    _encode_av1_vaapi,
    _encode_h264_nvenc,
    _encode_h264_vaapi,
    _encode_hevc_nvenc,
    _encode_hevc_vaapi,
    _encode_librav1e,
    _encode_libsvtav1,
    _encode_libvpx_vp9,
    _encode_libx264,
    _encode_libx265,
    _encode_vp9_vaapi,
    _encode_vvc,
)

RESOLUTION = [256, 256]
FFMPEG_CMD_READ = [
    "ffmpeg", "-hide_banner",
    "-f", "rawvideo",
    "-s", f"{RESOLUTION[1]}x{RESOLUTION[0]}",
    "-pix_fmt", "yuv420p",
    "-r", "24",
    "-i", "/dev/urandom",
    "-to", "0.25",
]


def encode(encoder: str, cmd_creator: callable) -> None:
    """General encoding test."""
    for mode, quality, effort, pix_fmt in itertools.product(
        ["vbr", "cbr"], [0.33, 0.66], ["fast", "medium", "slow"], ["yuv420p", "yuv420p10le"],
    ):
        cmd_middle = cmd_creator(
            effort=effort,
            encoder=encoder,
            mode=mode,
            pix_fmt=pix_fmt,
            quality=quality,
            resolution=RESOLUTION,
            threads=8,
        )
        cmd = [*FFMPEG_CMD_READ, *cmd_middle, "-f", "null", "-"]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as err:
            msg = " ".join(map(shlex.quote, cmd))
            raise RuntimeError(msg) from err


def test_encode_av1_nvenc() -> None:
    """Perform the ffmpeg encoding test on av1_nvenc."""
    encode("av1_nvenc", _encode_av1_nvenc)


def test_encode_av1_vaapi() -> None:
    """Perform the ffmpeg encoding test on av1_vaapi."""
    encode("av1_vaapi", _encode_av1_vaapi)


def test_encode_h264_nvenc() -> None:
    """Perform the ffmpeg encoding test on h264_nvenc."""
    encode("h264_nvenc", _encode_h264_nvenc)


def test_encode_h264_vaapi() -> None:
    """Perform the ffmpeg encoding test on h264_vaapi."""
    encode("h264_vaapi", _encode_h264_vaapi)


def test_encode_hevc_nvenc() -> None:
    """Perform the ffmpeg encoding test on hevc_nvenc."""
    encode("hevc_nvenc", _encode_hevc_nvenc)


def test_encode_hevc_vaapi() -> None:
    """Perform the ffmpeg encoding test on hevc_vaapi."""
    encode("hevc_vaapi", _encode_hevc_vaapi)


def test_encode_librav1e() -> None:
    """Perform the ffmpeg encoding test on librav1e."""
    encode("librav1e", _encode_librav1e)


def test_encode_libsvtav1() -> None:
    """Perform the ffmpeg encoding test on libsvtav1."""
    encode("libsvtav1", _encode_libsvtav1)


def test_encode_libvpx_vp9() -> None:
    """Perform the ffmpeg encoding test on libvpx-vp9."""
    encode("libvpx-vp9", _encode_libvpx_vp9)


def test_encode_libx264() -> None:
    """Perform the ffmpeg encoding test on libx264."""
    encode("libx264", _encode_libx264)


def test_encode_libx265() -> None:
    """Perform the ffmpeg encoding test on libx265."""
    encode("libx265", _encode_libx265)


def test_encode_vp9_vaapi() -> None:
    """Perform the ffmpeg encoding test on vp9_vaapi."""
    encode("vp9_vaapi", _encode_vp9_vaapi)


def test_encode_vvc() -> None:
    """Perform the ffmpeg encoding test on vvc."""
    encode("vvc", _encode_vvc)
