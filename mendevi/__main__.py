#!/usr/bin/env python3

"""Command line interface entry point."""

import click

from mendevi.cli.encode import main as main_encode
from mendevi.cli.prepare import main as main_prepare


@click.group()
def main() -> int:
    """Performs video transcoding measurements."""
    return 0


main.add_command(main_encode, "encode")
main.add_command(main_prepare, "prepare")


if __name__ == "__main__":
    main()
