"""CLI entry point to visualize database data."""

import importlib
import pathlib

import click
from context_verbose import Printer
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import PythonLexer

from mendevi.cst.labels import LABELS
from mendevi.database.meta import get_extractor
from mendevi.download.decapsulation import retrive_file
from mendevi.plot.printer import printer, safe_lbl

from .parse import parse_expr, parse_videos_database

NAMES_DOC = "        ".join(
    f"* {n}: {get_extractor(n).legend}.\n" for n in LABELS
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
table : str, optional
    The main sql table juste after the FROM in SELECT.
sub : tuple[tuple[str, str]], optional
    This allows to substitute text in the generated python code, before calling it to draw the plot.
    The provided parameters are pairs of regex expression 'pattern' and 'repl'.
    It is given as argument to the function ``re.sub``.
"""


def _parse_args(prt: Printer, kwargs: dict) -> None:
    """Verification of the arguments."""
    # x
    assert "x" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["x"], tuple), kwargs["x"].__class__.__name__
    assert kwargs["x"], "you must provide the -x option"
    for i, expr in enumerate(kwargs["x"]):
        parse_expr(expr, prt, f"x_{i:<8}")

    # y
    assert "y" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["y"], tuple), kwargs["y"].__class__.__name__
    assert kwargs["y"], "you must provide the -y option"
    for i, expr in enumerate(kwargs["y"]):
        parse_expr(expr, prt, f"y_{i:<8}")

    # color
    kwargs["color"] = kwargs.get("color")
    parse_expr(kwargs["color"], prt, "color     ")

    # marker
    kwargs["marker"] = kwargs.get("marker")
    parse_expr(kwargs["marker"], prt, "marker    ")

    # error
    kwargs["error"] = kwargs.get("error")
    parse_expr(kwargs["error"], prt, "error     ")

    # window
    kwargs["window"] = kwargs.get("window")
    if kwargs["window"] is not None:
        kwargs[
            {
                (False, True, False, True): "window_y",
                (True, False, True, False): "window_x",
                (True, True, False, True): "window_y",
                (True, True, True, False): "window_x",
                (False, True, False, False): "window_y",
                (True, False, False, False): "window_x",
            }.get(
                (
                    kwargs.get("window_x") is None,
                    kwargs.get("window_y") is None,
                    len(kwargs["x"]) == 1,
                    len(kwargs["y"]) == 1,
                ),
                "window_y",
            )
        ] = kwargs["window"]

    # window_x
    kwargs["window_x"] = kwargs.get("window_x")
    parse_expr(kwargs["window_x"], prt, "window x  ")

    # window_y
    kwargs["window_y"] = kwargs.get("window_y")
    parse_expr(kwargs["window_y"], prt, "window y  ")

    # filter
    kwargs["filter"] = kwargs.get("filter")
    parse_expr(kwargs["filter"], prt, "filter    ")

    # table
    kwargs["table"] = kwargs.get("table")
    if kwargs["table"] is not None:
        assert isinstance(kwargs["table"], str), kwargs["table"].__class__.__name__
        prt.print(f"table     : {kwargs['table']}")

    # sub
    kwargs["sub"] = kwargs.get("sub", ())
    assert isinstance(kwargs["sub"], tuple), kwargs["sub"].__class__.__name__
    assert all(isinstance(s, tuple) and len(s) == 2 for s in kwargs["sub"]), kwargs["sub"]
    prt.print(f"code sub  : {' and '.join(f'{p} -> {r}' for p, r in kwargs['sub'])}")


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
    help="Data selection python expression.",
)
@click.option(
    "-p", "--print",
    is_flag=True,
    help="Flag to print the source code.",
)
@click.option(
    "-t", "--table",
    type=str,
    help="Form the SQL query around this table.",
)
@click.option(
    "-s", "--sub",
    type=str,
    nargs=2,
    multiple=True,
    help="Pair of regex expression 'pattern' and 'repl' to substitute in generated code.",
)
def main(database: str, **kwargs: dict) -> None:
    """See docstring at DOCSTRING."""
    # parse args
    with Printer("Parse configuration...") as prt:
        database = retrive_file(database)
        _, database = parse_videos_database(prt, (), database)
        _parse_args(prt, kwargs)

    # get title name
    path = (
        pathlib.Path.cwd() / (
            f"{'_'.join(map(safe_lbl, kwargs['y']))}"
            "_as_a_function_of_"
            f"{'_'.join(map(safe_lbl, kwargs['x']))}"
            ".py"
        )
    )

    # get code content
    code = printer(database=database, **kwargs, path=path)
    if kwargs.get("print", False):
        print("**********************************PYTHON CODE**********************************")
        print(highlight(code, PythonLexer(), TerminalFormatter()))
        print("*******************************************************************************")
    with path.open("w", encoding="utf-8") as file:
        file.write(code)

    # excecute code
    spec = importlib.util.spec_from_file_location(path.stem, path)
    modulevar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulevar)
    modulevar.main(modulevar.read_sql(database))


# fill the documentation
main.__doc__ = DOCSTRING
