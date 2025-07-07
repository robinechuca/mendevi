#!/usr/bin/env python3

"""Defines the different video profiles used.

For YouTube <https://support.google.com/youtube/answer/1722171>:
- muxer mp4
- audio aac stereo 384kbit/s 48kHz
- video h264 yuv420p 1080p 8Mbit/s 29.97fps
<https://trac.ffmpeg.org/wiki/Encode/YouTube>
<https://gist.github.com/mikoim/27e4e0dc64e384adbcb91ff10a2d3678>
"""

from fractions import Fraction


PROFILES = {
    "sd": {
        "fps": Fraction(24000, 1001),
        "matrix": "smpte170m",
        "pix_fmt": "yuv420p",
        "primaries": "smpte170m",
        "range": "tv",
        "shape": (720, 480),
        "transfer": "smpte170m",
    },
    "hd": {
        "fps": Fraction(25000, 1001),
        "matrix": "bt709",
        "pix_fmt": "yuv420p",
        "primaries": "bt709",  # sRGB
        "range": "tv",
        "shape": (1280, 720),
        "transfer": "iec61966-2-1, iec61966_2_1",  # sRGB
    },
    "uhd": {
        "fps": Fraction(30000, 1001),
        "matrix": "bt709",
        "pix_fmt": "yuv420p10le",
        "primaries": "bt709",
        "range": "tv",
        "shape": (1920, 1080),
        "transfer": "bt709",
    },
    "hd4k": {  # partialy given by https://trac.ffmpeg.org/wiki/Encode/AV1
        "fps": Fraction(60000, 1001),
        "matrix": "bt2020nc",
        "pix_fmt": "yuv420p10le",
        "primaries": "bt2020",
        "range": "pc",
        "shape": (3840, 2160),
        "transfer": "smpte2084",
    },
}
