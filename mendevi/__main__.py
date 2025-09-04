#!/usr/bin/env python3

"""Command line interface entry point."""

import click

from mendevi.cli.decode import main as main_decode
from mendevi.cli.doc import main as main_doc
from mendevi.cli.encode import main as main_encode
from mendevi.cli.prepare import main as main_prepare
from mendevi.cli.probe import main as main_probe


@click.group()
def main() -> int:
    """Performs video transcoding measurements."""
    return 0


main.add_command(main_decode, "decode")
main.add_command(main_doc, "doc")
main.add_command(main_encode, "encode")
main.add_command(main_prepare, "prepare")
main.add_command(main_probe, "probe")


if __name__ == "__main__":
    main()
