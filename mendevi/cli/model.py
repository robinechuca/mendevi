"""CLI entry point to handle models."""

import pathlib
import pickle

import click
from context_verbose import Printer

from mendevi.cst.labels import LABELS
from mendevi.cst.model import import_all_models
from mendevi.database.create import is_sqlite
from mendevi.database.meta import get_extractor
from mendevi.download.decapsulation import retrive_file

from .parse import parse_expr

NAMES_DOC = "        ".join(
    f"* {n}: {get_extractor(n).legend}.\n" for n in LABELS
)
TRAIN_DOCSTRING = f"""Create a new instance of a model, train it and store it.

\b
Parameters
----------
ctx
    Context of the ``mendevi model`` group.
**kwargs: dict
    Please refer to the detailed arguments below.
class : str
    The class name of the python model. Any of {sorted(import_all_models())}
input, output : str
    The list of the input / output labels of the model.
    Possible values are:
        {NAMES_DOC}
\b
table : str, optional
    The main sql table juste after the FROM in SELECT.
"""


def _parse_args(prt: Printer, kwargs: dict) -> None:
    """Verification of the arguments."""
    # input
    assert "input" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["input"], tuple), kwargs["input"].__class__.__name__
    assert kwargs["input"], "you must provide the -input option"
    for i, expr in enumerate(kwargs["input"]):
        parse_expr(expr, prt, f"input {i:<4}")

    # output
    assert "output" in kwargs, sorted(kwargs)
    assert isinstance(kwargs["output"], tuple), kwargs["output"].__class__.__name__
    assert kwargs["output"], "you must provide the -output option"
    for i, expr in enumerate(kwargs["output"]):
        parse_expr(expr, prt, f"output {i:<3}")

    # table
    kwargs["table"] = kwargs.get("table")
    if kwargs["table"] is not None:
        assert isinstance(kwargs["table"], str), kwargs["table"].__class__.__name__
        prt.print(f"table     : {kwargs['table']}")


@click.group
@click.option(
    "-n", "--name",
    default="mendevi",
    help="The name, which identifies this specific model",
)
@click.pass_context
def main(ctx: click.Context, name: str) -> None:
    """Play with video predictive models."""
    ctx.ensure_object(dict)
    ctx.obj["name"] = name


@click.command(help=TRAIN_DOCSTRING)
@click.pass_context
@click.option(
    "-c", "--class",
    type=click.Choice(sorted(import_all_models())),
    default="LinearRegression",
    help="The model python class name",
)
@click.option(
    "-i", "--input",
    type=str,
    multiple=True,
    help="The name of all input parameters",
)
@click.option(
    "-o", "--output",
    type=str,
    multiple=True,
    help="The name of all output parameters",
)
@click.option(
    "-d", "--train",
    type=str,
    required=True,
    help="The traing dataset path or name",
)
@click.option(
    "-t", "--table",
    type=str,
    help="Form the SQL query around this table.",
)
def train(ctx: click.Context, **kwargs: dict) -> None:
    """See docstring at TRAIN_DOCSTRING."""
    # parse args
    with Printer("Parse configuration...") as prt:
        assert "train" in kwargs
        train = retrive_file(kwargs["train"])
        assert is_sqlite(train)
        _parse_args(prt, kwargs)

    # create and train model
    model_cls = import_all_models()[kwargs["class"]]
    model = model_cls(input_labels=kwargs["input"], output_labels=kwargs["output"])
    model.fit(train, table=kwargs["table"])

    # save the model
    cachedir = pathlib.Path.home() / ".cache" / "mendevi"
    cachedir.mkdir(mode=0o777, parents=True, exist_ok=True)
    path = (cachedir / ctx.obj["name"]).with_suffix(".pkl")
    with Printer(f"Save model into {path}...") as prt, path.open("wb") as file:
        pickle.dump(model, file)
        prt.print_time()


@click.command
@click.pass_context
def predict(ctx: click.Context) -> None:
    """Load an existing model to perform predictions."""
    raise NotImplementedError


@click.command
@click.pass_context
def benchmark(ctx: click.Context) -> None:
    """Evaluate and display the model's performance."""
    raise NotImplementedError


main.add_command(train)
main.add_command(predict)
main.add_command(benchmark)

# fill the documentation
train.__doc__ = TRAIN_DOCSTRING
