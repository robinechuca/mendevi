"""Download and decapsule a file."""


import click
from context_verbose import Printer

from mendevi.download.decapsulation import retrive_file


@click.command()
@click.argument("file", type=str)
def main(file: str) -> None:
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
