#!/usr/bin/env python3

"""Command line interface entry point."""

import click

from .encode import main as main_encode


@click.group()
def main() -> int:
    """Performs video transcoding measurements."""
    return 0


main.add_command(main_encode, "encode")
# main.add_command(main_decode, "decode")


if __name__ == "__main__":
    main()
