#!/usr/bin/env python3

"""Command line interface entry point."""

import click

from .draw import main as main_draw
from .encode import main as main_encode
from .merge import main as main_merge


@click.group()
def main() -> int:
    """Performs video transcoding measurements."""
    return 0


main.add_command(main_draw, "draw")
main.add_command(main_encode, "encode")
main.add_command(main_merge, "merge")


if __name__ == "__main__":
    main()
