# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Display the version."""

import click

from mendevi import __version__


@click.command()
def main() -> None:
    """Display the mendevi version."""
    click.echo(__version__)
