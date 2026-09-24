# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Download and decapsule a file."""


import click
from context_verbose import Printer

from mendevi.download.decapsulation import retrive_file


@click.command()
@click.argument("file", type=str)
def main(file: str) -> None:
    """Torrent download with optional extraction and decompression.

    \b
    Automates the full retrieval process for large files: downloads them via torrent,
    then extracts and decompresses them if necessary,
    and returns the path to the final ready-to-use file.

    \b
    Parameters
    ----------
    file : pathlike
        The filename to get.

    """
    with Printer(f"Get {file!r}...", color="cyan") as prt:
        path = retrive_file(file)
        prt.print(f"final file: {path}")
