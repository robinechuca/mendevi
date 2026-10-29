# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Start jupyter-notebook in the examples folder."""

import subprocess
import sys

import click

from mendevi.utils import get_project_root


@click.command()
@click.option("--no-open", is_flag=True, help="Do not open the documentation in the browser.")
def main(*, no_open: bool = False) -> None:
    """Start jupyter-notebook in the examples folder."""
    assert isinstance(no_open, bool), no_open.__class__.__name__
    root = get_project_root().parent / "examples"
    browser_flag = ["--no-browser"] if no_open else ["--expose-app-in-browser"]
    subprocess.run(
        ["jupyter-notebook", str(root), *browser_flag],
        check=False,
        stdout=sys.stderr,
    )
