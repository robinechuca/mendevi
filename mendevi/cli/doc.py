"""Compile and show the documentation."""

import subprocess
import sys

import click

from mendevi.utils import get_project_root


@click.command()
@click.option("-c", "--recompile", is_flag=True, help="Force to recompile the documentation.")
@click.option("--no-open", is_flag=True, help="Do not open the documentation in the browser.")
def main(*, recompile: bool = False, no_open: bool = False) -> None:
    """Compile and show the documentation."""
    assert isinstance(recompile, bool), recompile.__class__.__name__
    assert isinstance(no_open, bool), no_open.__class__.__name__
    root = get_project_root().parent / "docs"
    index = (root / "build" / "html" / "index.html").resolve()
    if not index.exists() or recompile:
        subprocess.run(
            ["make", "clean"],
            check=True,
            cwd=root,
            stdout=sys.stderr,
        )
        subprocess.run(
            ["make", "html"],
            check=True,
            cwd=root,
            stdout=sys.stderr,
        )
    click.echo(index)
    if not no_open:
        subprocess.run(
            ["xdg-open", str(index)],  # default browser
            check=False,
            stdout=sys.stderr,
        )
