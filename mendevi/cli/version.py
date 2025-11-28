"""Display the version."""

import click

from mendevi import __version__


@click.command()
def main() -> None:
    """Display the mendevi version."""
    click.echo(__version__)
