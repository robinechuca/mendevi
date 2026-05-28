"""CLI entry point to handle models."""

import itertools
import math
import pathlib
import pickle
import subprocess

import click
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import torch
from context_verbose import Printer

from mendevi.cst.labels import LABELS
from mendevi.cst.model import import_all_models
from mendevi.cst.plot import COLORS
from mendevi.database.create import is_sqlite
from mendevi.database.meta import get_extractor
from mendevi.download.decapsulation import retrive_file
from mendevi.models.base import Model

from .parse import parse_expr

FIGSIZE = (6.0, 4.0)  # (width, height)
FIGNAME = pathlib.Path("violin.pdf")
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
select : str, optional
    This allows you to filter the data to select only a portion of it.
    The character string provided must be a Boolean Python expression
    that returns True to keep the data. For example: ``enc_duration > 10 and profile == "fhd"``.
table : str, optional
    The main sql table juste after the FROM in SELECT.
"""


class _ModelUnpickler(pickle.Unpickler):
    """Solve abstract definition missing, because pickle shortcut __call__."""

    def find_class(self, module: str, name: str) -> type:
        cls = super().find_class(module, name)
        if isinstance(cls, type) and getattr(cls, "__abstractmethods__", None):
            cls.__abstractmethods__ = frozenset()
        return cls


def _parse_args_train(prt: Printer, kwargs: dict) -> None:
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

    # filter
    kwargs["filter"] = kwargs.get("filter")
    parse_expr(kwargs["filter"], prt, "filter    ")

    # table
    kwargs["table"] = kwargs.get("table")
    if kwargs["table"] is not None:
        assert isinstance(kwargs["table"], str), kwargs["table"].__class__.__name__
        prt.print(f"table     : {kwargs['table']}")

    # validation
    kwargs["validation"] = kwargs.get("validation", 0.2)
    assert isinstance(kwargs["validation"], float), kwargs["validation"].__class__.__name__
    assert 0.0 <= kwargs["validation"] < 1.0, kwargs["validation"]
    prt.print(f"validation: {kwargs['validation']:.1%}")


def _parse_name(prt: Printer, name: str, *, must_exists: bool = False) -> pathlib.Path:
    """Verification and creation or parent dirs."""
    path = pathlib.Path(name)
    if (rootdir := path.parent) == pathlib.Path():
        rootdir = pathlib.Path.home() / ".cache" / "mendevi"
    path = (rootdir / path.name).with_suffix(".pkl")
    if must_exists:
        assert path.exists(), path
    rootdir.mkdir(mode=0o777, parents=True, exist_ok=True)
    prt.print(f"data path : {path}")
    return path


@click.group
def main() -> None:
    """Play with video predictive models."""


@click.command(help=TRAIN_DOCSTRING)
@click.option(
    "-n", "--name",
    default="mendevi",
    help="The name, which identifies this specific model",
)
@click.option(
    "-c", "--class",
    type=click.Choice(sorted(import_all_models())),
    default="LR",
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
    "-v", "--validation",
    type=float,
    default=0.2,
    help="The validation dataset percentage",
)
@click.option(
    "--select", "-s",
    type=str,
    help="Data selection python expression.",
)
@click.option(
    "-t", "--table",
    type=str,
    help="Form the SQL query around this table.",
)
def train(**kwargs: dict) -> None:
    """See docstring at TRAIN_DOCSTRING."""
    # parse args
    with Printer("Parse configuration...") as prt:
        model_path = _parse_name(prt, kwargs["name"])
        assert "train" in kwargs
        train = retrive_file(kwargs["train"])
        assert is_sqlite(train)
        _parse_args_train(prt, kwargs)

    # exclusion of invalid, unwanted and validation-only data
    select = " and ".join(
        f"({expr})" for expr in (
            *(kwargs["select"] or []),
            " and ".join(f"{lbl} is not None" for lbl in kwargs["output"]),
            f"uniform(({', '.join(kwargs['output'])})) > {kwargs['validation']}",
        )
    )

    # create and train model
    model_cls = import_all_models()[kwargs["class"]]
    model = model_cls(input_labels=kwargs["input"], output_labels=kwargs["output"])
    model.fit(train, select=select, table=kwargs["table"])

    # validate model
    select = " and ".join(
        f"({expr})" for expr in (
            *(kwargs["select"] or []),
            " and ".join(f"{lbl} is not None" for lbl in kwargs["output"]),
            f"uniform(({', '.join(kwargs['output'])})) <= {kwargs['validation']}",
        )
    )
    model.validate(train, select=select, table=kwargs["table"])

    # save the model
    with Printer(f"Save model into {model_path}..."), model_path.open("wb") as file:
        kwargs["train"] = train
        pickle.dump(model, file)
        prt.print_time()


@click.command
@click.pass_context
def predict(ctx: click.Context) -> None:
    """Load an existing model to perform predictions."""
    # parse args
    with Printer("Parse configuration...") as prt:
        model_path = _parse_name(prt, ctx.obj["name"], must_exists=True)

    # load the model
    with Printer(f"Load model from {model_path}...") as prt, model_path.open("rb") as file:
        model = _ModelUnpickler(file).load()
        prt.print_time()

    raise NotImplementedError


@click.command
@click.option(
    "-n", "--name",
    multiple=True,
    help="The names of the models to be compared",
)
@click.option(
    "-o", "--output",
    multiple=True,
    help="The column labels names, default autodetect",
)
@click.option(
    "-l", "--limit",
    type=float,
    help="The max error limit",
)
def benchmark(**kwargs: dict) -> None:
    """Evaluate and display the model's performance.

    \b
    Parameters
    ----------
    **kwargs: dict
        See above.
    name : tuple[pathlike]
        The name, the path or the identifier of the models to be compared.
        You must provide at least one.
    output : tuple[str]
        The names of the labels to be displayed on each column.
        By default, the labels common to all models are used.
    limit : float, optional
        The maximum value of the histogram, which corresponds to the maximum value on the x-axis.
        By default, this value is calculated included 95% of the values in the histogram.

    \b
    * Parametre de filtre pour limiter les out-layers (histograme bien étalé) (Sur l'erreur)
    * Selection de la fenetre min-max sur la grandeur estimée de sortie
    * Resortir un tableau

    """
    # parse args
    with Printer("Parse configuration...") as prt:
        models_path = [_parse_name(prt, name, must_exists=True) for name in kwargs.get("name", [])]
        assert models_path, "you must provide at least one model name with the -n option"

    # load the models
    models = []  # keeping order is important
    with Printer("Load the models...") as prt:
        for model_path in models_path:
            with model_path.open("rb") as file:
                prt.print(f"load model {model_path}")
                models.append(_ModelUnpickler(file).load())
        prt.print_time()

    # get available out labels
    output_labels = set(kwargs.get("output", ()))
    output_labels_candidates = set.intersection(*(set(model.output_labels) for model in models))
    assert output_labels.issubset(output_labels_candidates), (
        f"the labels {output_labels-output_labels_candidates} are not available in all models, "
        f"available labels are {output_labels_candidates}"
    )
    output_labels = output_labels or output_labels_candidates
    assert output_labels, "the models do not predict the same thing"

    # compute all the MAPEs
    def _compute_mape(model: Model, output_label: str) -> torch.Tensor:
        pred, val = torch.cat([clus[output_label] for clus in model.accuracy.values()], dim=1)
        return ((val - pred).abs() / (val.abs() + torch.finfo(torch.float32).eps)).mean(dim=1)
    all_mape: dict[str, list[torch.Tensor]] = {  # to each output lbl, associate the 1d MAPE
        output_label: [_compute_mape(model, output_label) for model in models]
        for output_label in output_labels
    }

    # get boundaries
    if (xlim := kwargs.get("limit")) is None:
        xlim = {
            output_label: max(torch.quantile(m, .95) for m in mape)
            for output_label, mape in all_mape.items()
        }
    else:
        assert isinstance(xlim, float), xlim.__class__.__name__
        xlim = dict.fromkeys(output_labels, xlim)

    # display
    nrows, ncols = len(models), len(output_labels)
    fig = plt.figure(
        layout="constrained",
        figsize=(FIGSIZE[0] * math.sqrt(ncols), FIGSIZE[1] * math.sqrt(nrows)),
    )
    fig.supxlabel("Absolute Percentage Error")
    axes = fig.subplots(
        nrows,
        ncols,
        squeeze=False,
        sharex="col",
        sharey="all",
    )
    # set the titles in grid
    for j, output_label in enumerate(output_labels):
        axes[0, j].set_xlabel(output_label, loc="center")
        axes[0, j].xaxis.set_label_position("top")
    for i, model_path in enumerate(models_path):
        axes[i, 0].set_ylabel(model_path.stem, loc="center")
        axes[i, 0].yaxis.set_label_position("left")
    # fill axes
    for (i, _model), (j, output_label) in itertools.product(
        enumerate(models), enumerate(output_labels),
    ):
        # compute hist and data
        mape = all_mape[output_label][i]
        bins = math.ceil(math.sqrt(len(mape))) + 1
        maxi = xlim[output_label] / 0.95
        width = maxi / bins
        hist = torch.histc(mape, bins=bins, min=0, max=maxi)
        hist /= hist.max()
        quants = torch.quantile(mape, torch.asarray([0.05, 0.25, 0.5, 0.75, 0.95]))

        # plot data
        axe = axes[i, j]
        axe.set_yticks([])  # no graduations on vertical axis
        axe.xaxis.set_major_formatter(mtick.PercentFormatter(1))
        axe.set_xlim(0, maxi)

        axe.bar(
            [quants[1]], [1],
            width=quants[2]-quants[1], align="edge", color=COLORS[0], label="second quartile",
        )
        axe.bar(
            [quants[2]], [1],
            width=quants[3]-quants[2], align="edge", color=COLORS[1], label="third quartile",
        )
        axe.bar(
            torch.linspace(0, width*(bins-1), bins), hist,
            width=width, align="edge", color=COLORS[2], label="histogram",
        )

        axe.plot(
            [[quants[0], quants[1], quants[2], quants[3], quants[4]],
             [quants[0], quants[1], quants[2], quants[3], quants[4]]],
            [[.75, 1, 1, 1, .75],
             [.25, 0, 0, 0, .25]],
            color=COLORS[4],
        )
        axe.plot(
            [[quants[0], quants[1], quants[1], quants[3]],
             [quants[1], quants[3], quants[3], quants[4]]],
            [[.5, 1, 0, .5],
             [.5, 1, 0, .5]],
            color=COLORS[4],
        )

    lines, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(lines, labels, loc="outside upper center", ncols=3)

    plt.savefig(FIGNAME, format=FIGNAME.suffix[1:], transparent=False)
    subprocess.run(["pdfcrop", FIGNAME, FIGNAME], check=False)
    plt.show()


main.add_command(train)
main.add_command(predict)
main.add_command(benchmark)

# fill the documentation
train.__doc__ = TRAIN_DOCSTRING
