#!/usr/bin/env python3

"""Download and decapsule a file."""


from context_verbose import Printer
import click

from mendevi.download.decapsulation import retrive_file


@click.command()
@click.argument("file", type=str)
def main(file: str):
    """Download and decapsule a file.

    \b
    Parameters
    ----------
    file : pathlike
        The filename to get.
    """
    with Printer(f"Get {file!r}...", color="cyan") as prt:
        path = retrive_file(file)
        prt.print(f"final file: {path}")
