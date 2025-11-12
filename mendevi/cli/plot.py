#!/usr/bin/env python3

"""CLI entry point to visualize database data."""

import importlib
import pathlib

import click
from context_verbose import Printer
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import PythonLexer

from mendevi.cst.labels import LABELS
from mendevi.database.meta import extract_names, get_extractor
from mendevi.download.decapsulation import retrive_file
from mendevi.plot.printer import printer, safe_lbl

from .parse import parse_videos_database

NAMES_DOC = "        ".join(
    f"* {n}: {get_extractor(n).label}.\n" for n in LABELS
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
\b
color, marker : str, optional
    All points with the same value for this variable will be displayed in the same color and marker.
    Conversely, this allows points that do not share this criterion to be visually separated.
    The possible values are the same as for the x and y parameters.
error : str, optional
    Allows you to average several points within the same error bar.
    The string provided is a Python expression or variable.
    All points with the same image across this function are grouped together.
window : str, optional
    Rather than putting everything in the same chart, this allows you to create sub-windows.
    There will be as many sub-windows as there are different values taken by this criterion.
    The possible values are the same as for the x and y parameters.
window_x, window_y : str, optional
    Same as window, but with precision on the axis on which to develop.
filter : str, optional
    This allows you to filter the data to select only a portion of it.
    The character string provided must be a Boolean Python expression
    that returns True to keep the data. For example: ``enc_duration > 10 and profile == "fhd"``.
"""


def _parse_args(prt: Printer, kwargs: dict):
    """Verification of the arguments."""
    # x
    assert "x" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["x"], tuple), kwargs["x"].__class__.__name__
    assert kwargs["x"], "you must provide the -x option"
    assert all(isinstance(x, str) and extract_names(x).issubset(LABELS) for x in kwargs["x"]), (
        f"{set(lbl for ls in kwargs['x'] for lbl in extract_names(ls))-set(LABELS)} "
        "are invalid names, "
        f"it has to be one of {LABELS}"
    )
    prt.print(f"x         : {', '.join(kwargs['x'])}")

    # y
    assert "y" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["y"], tuple), kwargs["y"].__class__.__name__
    assert kwargs["y"], "you must provide the -y option"
    assert all(isinstance(y, str) and extract_names(y).issubset(LABELS) for y in kwargs["y"]), (
        f"{set(lbl for ls in kwargs['y'] for lbl in extract_names(ls))-set(LABELS)} "
        "are invalid names, "
        f"it has to be one of {LABELS}"
    )
    prt.print(f"y         : {', '.join(kwargs['y'])}")

    # color
    kwargs["color"] = kwargs.get("color")
    if kwargs["color"] is not None:
        assert isinstance(kwargs["color"], str), kwargs["color"].__class__.__name__
        names = extract_names(kwargs["color"])
        assert names.issubset(LABELS), \
            f"{names-set(LABELS)} are invalid names, it has to be one of {LABELS}"
        prt.print(f"color     : {kwargs['color']}")

    # marker
    kwargs["marker"] = kwargs.get("marker")
    if kwargs["marker"] is not None:
        assert isinstance(kwargs["marker"], str), kwargs["marker"].__class__.__name__
        names = extract_names(kwargs["marker"])
        assert names.issubset(LABELS), \
            f"{names-set(LABELS)} are invalid names, it has to be one of {LABELS}"
        prt.print(f"marker    : {kwargs['marker']}")

    # error
    kwargs["error"] = kwargs.get("error")
    if kwargs["error"] is not None:
        assert isinstance(kwargs["error"], str), kwargs["error"].__class__.__name__
        names = extract_names(kwargs["error"])
        assert names.issubset(LABELS), \
            f"{names-set(LABELS)} are invalid names, it has to be one of {LABELS}"
        prt.print(f"error     : {kwargs['error']}")

    # window
    kwargs["window"] = kwargs.get("window")
    if kwargs["window"] is not None:
        match (  # preference for y axis
            kwargs.get("window_x") is None,
            kwargs.get("window_y") is None,
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
    kwargs["window_x"] = kwargs.get("window_x")
    if kwargs["window_x"] is not None:
        assert isinstance(kwargs["window_x"], str), kwargs["window_x"].__class__.__name__
        names = extract_names(kwargs["window_x"])
        assert names.issubset(LABELS), \
            f"{names-set(LABELS)} are invalid names, it has to be one of {LABELS}"
        prt.print(f"window x  : {kwargs['window_x']}")

    # window_y
    kwargs["window_y"] = kwargs.get("window_y")
    if kwargs["window_y"] is not None:
        assert isinstance(kwargs["window_y"], str), kwargs["window_y"].__class__.__name__
        names = extract_names(kwargs["window_y"])
        assert names.issubset(LABELS), \
            f"{names-set(LABELS)} are invalid names, it has to be one of {LABELS}"
        prt.print(f"window y  : {kwargs['window_y']}")

    # filter
    kwargs["filter"] = kwargs.get("filter")
    if kwargs["filter"] is not None:
        assert isinstance(kwargs["filter"], str), kwargs["filter"].__class__.__name__
        names = extract_names(kwargs["filter"])
        assert names.issubset(LABELS), \
            f"{names-set(LABELS)} are invalid names, it has to be one of {LABELS}"
        prt.print(f"filter    : {kwargs['filter']}")


@click.command(help=DOCSTRING)
@click.argument("database", type=click.Path())
@click.option(
    "-x",
    type=str,
    multiple=True,
    help="The code for the value to be displayed on the x-axis.",
)
@click.option(
    "-y",
    type=str,
    multiple=True,
    help="The code for the value to be displayed on the y-axis.",
)
@click.option(
    "-c", "--color",
    type=str,
    help="The discriminating criterion for colour.",
)
@click.option(
    "-m", "--marker",
    type=str,
    help="The discriminating criterion for marker.",
)
@click.option(
    "-w", "--window",
    type=str,
    help="The criterion on which to separate into sub-windows.",
)
@click.option(
    "-wx", "--window-x",
    type=str,
    help="The criterion on which to separate into sub-windows along x axis.",
)
@click.option(
    "-wy", "--window-y",
    type=str,
    help="The criterion on which to separate into sub-windows along y axis.",
)
@click.option(
    "-e", "--error",
    type=str,
    help="Merge criteria for the error bar.",
)
@click.option(
    "--filter", "-f",
    type=str,
    help="Data selection python expression",
)
@click.option(
    "-p", "--print",
    is_flag=True,
    help="Flag to print the source code.",
)
def main(database: str, **kwargs):
    """See docstring at DOCSTRING."""
    # parse args
    with Printer("Parse configuration...") as prt:
        database = retrive_file(database)
        _, database = parse_videos_database(prt, (), database)
        _parse_args(prt, kwargs)

    # get title name
    path = (
        pathlib.Path.cwd() / (
            f"{'_'.join(map(safe_lbl, kwargs['x']))}"
            "_as_a_function_of_"
            f"{'_'.join(map(safe_lbl, kwargs['y']))}"
            ".py"
        )
    )

    # get code content
    code = printer(database=database, **kwargs)
    if kwargs.get("print", False):
        print("**********************************PYTHON CODE**********************************")
        print(highlight(code, PythonLexer(), TerminalFormatter()))
        print("*******************************************************************************")
    with open(path, "w", encoding="utf-8") as file:
        file.write(code)

    # excecute code
    spec = importlib.util.spec_from_file_location(path.stem, path)
    modulevar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulevar)
    modulevar.main(modulevar.read_sql(database))


# fill the documentation
main.__doc__ = DOCSTRING
