"""Test the ffmpeg encoding command on a stupid example."""

import itertools
import typing

from mendevi.cmd import CmdFFMPEG
from mendevi.encoder import (
    _encode_av1_nvenc,
    _encode_av1_vaapi,
    _encode_h264_nvenc,
    _encode_h264_vaapi,
    _encode_hevc_nvenc,
    _encode_hevc_vaapi,
    _encode_libaomav1,
    _encode_libopenh264,
    _encode_librav1e,
    _encode_libsvtav1,
    _encode_libvpx_vp9,
    _encode_libx264,
    _encode_libx265,
    _encode_vp9_vaapi,
    _encode_vvc,
)

RESOLUTION = [256, 256]
GENERAL = [
    "-f", "rawvideo",
    "-s", f"{RESOLUTION[1]}x{RESOLUTION[0]}",
    "-pix_fmt", "yuv420p",
    "-r", "1",
    "-to", "2",
]


def encode(encoder: str, cmd_creator: typing.Callable) -> None:
    """General encoding test."""
    for mode, quality, effort, pix_fmt in itertools.product(
        ["vbr", "cbr"], [0.33, 0.66], ["fast", "medium", "slow"], ["yuv420p", "yuv420p10le"],
    ):
        general, vid_filter, encode = cmd_creator(
            effort=effort,
            encoder=encoder,
            mode=mode,
            pix_fmt=pix_fmt,
            quality=quality,
            resolution=RESOLUTION,
            threads=8,
        )
        cmd = CmdFFMPEG(
            video="/dev/urandom",
            vid_filter=vid_filter,
            encode=encode,
        )
        cmd.general = cmd.general + general + GENERAL
        cmd.run()


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


def test_encode_libaomav1() -> None:
    """Perform the ffmpeg encoding test on libaom-av1."""
    encode("libaom-av1", _encode_libaomav1)


def test_encode_libopenh264() -> None:
    """Perform the ffmpeg encoding test on libopenh264."""
    encode("libopenh264", _encode_libopenh264)


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
