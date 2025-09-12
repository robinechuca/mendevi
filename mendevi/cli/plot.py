#!/usr/bin/env python3

"""CLI entry point to visualize database data."""

from context_verbose import Printer
import click
import subprocess

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter

from mendevi.plot.axis import NAMES, get_label_extractor
from mendevi.plot.printer import printer
from .parse import parse_videos_database

NAMES_DOC = "        ".join(
    f"* {n}: {get_label_extractor(n)[0]}.\n" for n in NAMES
)
DOCSTRING = f"""Draw a chart from a database.

\b
Parameters
----------
database : pathlike, optional
    The path to the database where all measurements are stored.
    If a folder is provided, the database is created inside this folder.
x, y : tuple[str]
    The name of the x and y axes on each window. Possible values are:
        {NAMES_DOC}
color : str, optional
    All points with the same value for this variable will be displayed in the same colour.
    Conversely, this allows points that do not share this criterion to be visually separated.
    The possible values are the same as for the x and y parameters.
window : str, optional
    Rather than putting everything in the same chart, this allows you to create sub-windows.
    There will be as many sub-windows as there are different values taken by this criterion.
    The possible values are the same as for the x and y parameters.
window_x, window_y : str, optional
    Same as window, but with precision on the axis on which to develop.
"""


def _parse_args(prt: Printer, kwargs: dict):
    """Verification of the arguments."""
    # x
    assert "x" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["x"], tuple), kwargs["x"].__class__.__name__
    assert kwargs["x"], "you must provide the -x option"
    assert all(isinstance(x, str) and x in NAMES for x in kwargs["x"]), kwargs["x"]
    prt.print(f"x         : {', '.join(kwargs['x'])}")

    # y
    assert "y" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["y"], tuple), kwargs["y"].__class__.__name__
    assert kwargs["y"], "you must provide the -y option"
    assert all(isinstance(y, str) and y in NAMES for y in kwargs["y"]), kwargs["y"]
    prt.print(f"y         : {', '.join(kwargs['y'])}")

    # color
    kwargs["color"] = kwargs.get("color", None)
    if kwargs["color"] is not None:
        assert isinstance(kwargs["color"], str), kwargs["color"].__class__.__name__
        assert kwargs["color"] in NAMES, kwargs["color"]
        prt.print(f"color     : {kwargs['color']}")

    # window
    kwargs["window"] = kwargs.get("window", None)
    if kwargs["window"] is not None:
        match (  # preference for y axis
            kwargs.get("window_x", None) is None,
            kwargs.get("window_y", None) is None,
            len(kwargs["x"]) == 1,
            len(kwargs["y"]) == 1,
        ):
            case (False, True, False, True):
                kwargs["window_y"] = kwargs["window"]
            case (True, False, True, False):
                kwargs["window_x"] = kwargs["window"]
            case (True, True, False, True):
                kwargs["window_y"] = kwargs["window"]
            case (True, True, True, False):
                kwargs["window_x"] = kwargs["window"]
            case (False, True, False, False):
                kwargs["window_y"] = kwargs["window"]
            case (True, False, False, False):
                kwargs["window_x"] = kwargs["window"]
            case _:
                kwargs["window_y"] = kwargs["window"]

    # window_x
    kwargs["window_x"] = kwargs.get("window_x", None)
    if kwargs["window_x"] is not None:
        assert isinstance(kwargs["window_x"], str), kwargs["window_x"].__class__.__name__
        assert kwargs["window_x"] in NAMES, kwargs["window_x"]
        prt.print(f"window x  : {kwargs['window_x']}")

    # window_y
    kwargs["window_y"] = kwargs.get("window_y", None)
    if kwargs["window_y"] is not None:
        assert isinstance(kwargs["window_y"], str), kwargs["window_y"].__class__.__name__
        assert kwargs["window_y"] in NAMES, kwargs["window_y"]
        prt.print(f"window y  : {kwargs['window_y']}")


@click.command(help=DOCSTRING)
@click.argument("database", type=click.Path())
@click.option(
    "-x",
    type=click.Choice(NAMES),
    multiple=True,
    help="The code for the value to be displayed on the x-axis.",
)
@click.option(
    "-y",
    type=click.Choice(NAMES),
    multiple=True,
    help="The code for the value to be displayed on the y-axis.",
)
@click.option(
    "-c", "--color",
    type=click.Choice(NAMES),
    help="The discriminating criterion for colour.",
)
@click.option(
    "-w", "--window",
    type=click.Choice(NAMES),
    help="The criterion on which to separate into sub-windows."
)
@click.option(
    "--window-x",
    type=click.Choice(NAMES),
    help="The criterion on which to separate into sub-windows along x axis."
)
@click.option(
    "--window-y",
    type=click.Choice(NAMES),
    help="The criterion on which to separate into sub-windows along y axis."
)
def main(database: str, **kwargs):
    with Printer("Parse configuration...") as prt:
        _, database = parse_videos_database(prt, (), database)
        _parse_args(prt, kwargs)

    code = printer(database=database, **kwargs)
    print("**********************************PYTHON CODE**********************************")
    print(highlight(code, PythonLexer(), TerminalFormatter()))
    print("*******************************************************************************")
    with open("plot_autogenerated.py", "w", encoding="utf-8") as file:
        file.write(code)
    subprocess.run(["python", "plot_autogenerated.py"])

# fill the documentation
main.__doc__ = DOCSTRING
