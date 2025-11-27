"""Management of all unit tests."""

import click

from mendevi.testing.run import run_tests


@click.command()
@click.option("--debug", is_flag=True, help="Show more information on failure.")
@click.option("--skip-install", is_flag=True, help="Do not check the installation.")
@click.option("--skip-coding-style", is_flag=True, help="Do not check programation style.")
@click.option("--skip-slow", is_flag=True, help="Do not run the slow tests.")
def main(*, debug: bool = False, **kwargs: dict) -> int:
    """Run several tests."""
    return run_tests(
        debug=debug,
        skip_install=kwargs.get("skip_install", False),
        skip_coding_style=kwargs.get("skip_coding_style", False),
        skip_slow=kwargs.get("skip_slow", False),
    )
