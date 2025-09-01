#!/usr/bin/env python3

"""Parse and verify some user input."""

import re

import click



class PixelParamType(click.ParamType):
    """Parse the pixel format."""
    name = "pixel"

    def convert(self, value, param, ctx):
        value = value.lower()
        if not re.fullmatch(r"yuv4[24][024]p(?:10le|12le)?", value):
            self.fail(f"{value!r} is not a valid pixel format", param, ctx)
        return value


class ResolutionParamType(click.ParamType):
    """Parse the resolution."""
    name = "resolution"

    def convert(self, value, param, ctx):
        if (match := re.search(
            r"(?P<t1>he)?\D*(?P<d1>\d+)\D+?(?P<t2>w)?\D*(?P<d2>\d+)", value.lower()
        )) is None:
            self.fail(f"{value!r} is not a valid video shape", param, ctx)
        if match["t1"] == "he" or match["t2"] == "w":
            return (int(match["d1"]), int(match["d2"]))
        return (int(match["d2"]), int(match["d1"]))
