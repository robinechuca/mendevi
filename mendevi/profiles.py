#!/usr/bin/env python3

"""Defines the different video profiles used."""

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
