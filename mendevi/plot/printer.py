"""Generate a Python code that allows you to plot the graph."""

import datetime
import itertools
import logging
import re
import subprocess

from mendevi import __version__
from mendevi.cst.plot import COLORS, FIGSIZE, MARKERS, MARKERSIZE
from mendevi.database.extract import SqlLinker
from mendevi.database.meta import Scale, get_extractor, merge_extractors


def printer(**kwargs: dict) -> str:
    """Create an excecutable python code."""
    # create code
    code: list[str] = []
    code.extend(print_header())
    code.extend(print_import())
    code.extend(print_cst(**kwargs))
    code.extend(print_mean_std())
    code.extend(print_read_sql(**kwargs))
    code.extend(print_fill_axe(**kwargs))
    code.extend(print_main(**kwargs))
    code.extend(print_entry())
    code = "\n".join(code)

    # format code
    try:
        result = subprocess.run(
            ["ruff", "format", "--line-length", "100", "-"],
            input=code.encode(),
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        logging.getLogger(__name__).warning(
            "Ruff is not installed, please install it (uv pip install ruff)",
        )
    except subprocess.CalledProcessError as err:
        logging.getLogger(__name__).warning("Ruff formatting failed: %s", err.stderr.decode())
    else:
        code = result.stdout.decode()

    # substitution
    for pattern, repl in kwargs["sub"]:
        code = re.sub(pattern, repl, code)

    return code


def print_entry() -> list[str]:
    """Return the code of the entry point."""
    return [
        'if __name__ == "__main__":',
        "    values: dict[str] = read_sql(DATABASE)",
        "    main(values)",
        "",
    ]


def print_error(**kwargs: dict) -> list[str]:
    """Help for print_fill_axe."""
    if kwargs["error"] is not None:
        return [
            "",
            "# compute error bar",
            'errs = list(set(sub_values["error"]))  # list to frozen order',
            "xerr, yerr = {e: [] for e in errs}, {e: [] for e in errs}",
            'for x, y, err in zip(x_data, y_data, sub_values["error"]):',
            "    xerr[err].append(x)",
            "    yerr[err].append(y)",
            "xerr = [xerr[e] for e in errs]",
            "yerr = [yerr[e] for e in errs]",
            "x_data, xerr = zip(*map(mean_std, xerr))",
            "y_data, yerr = zip(*map(mean_std, yerr))",
            "",
        ]
    return [
        "xerr = None",
        "yerr = None",
    ]


def print_cst(**kwargs: dict) -> list[str]:
    """Return the code of the definition of the constants."""
    return [
        f"COLORS = {COLORS}",
        f"DATABASE = pathlib.Path({str(kwargs['database'])!r})",
        'FIGNAME = pathlib.Path(__file__).with_suffix(".svg")',
        f"FIGSIZE = {FIGSIZE}  # (width, height)",
        f"MARKERS = {MARKERS}  # list of dot shapes",
        f"MARKERSIZE = {MARKERSIZE}",
        "",
        "",
    ]


def print_grid(axe: str, dim: str, scale: Scale) -> list[str]:
    """Define the ticks rule and log or linear scale.

    Parameters
    ----------
    axe : str
        The acessor to the matplotlib axe.
    dim : str
        "x" or "y".
    scale : Scale
        Linear, logarithmic or discrete.

    """
    assert isinstance(axe, str), axe.__class__.__name__
    assert isinstance(scale, Scale), scale.__class__.__name__
    assert dim in {"x", "y"}, dim

    if scale == Scale.DISCRETE:
        logging.getLogger(__name__).warning("the axis %s should be display as bar plot", dim)
        return []
    if scale == Scale.LOGARITHMIC:
        return [
            f'{axe}.set_{dim}scale("log", base=10)  # or .set_{dim}scale("linear")',
            f'{axe}.grid(axis="{dim}", which="major")',
            f'{axe}.grid(axis="{dim}", which="minor", color="0.9")',
        ]
    if scale == Scale.LINEAR:
        return [
            f'{axe}.set_{dim}scale("linear")  # or .set_{dim}scale("log", base=10)',
            f'{axe}.grid(axis="{dim}", which="major")',
            f'{axe}.grid(axis="{dim}", which="minor", color="0.9")',
            f"ticks = {axe}.{dim}axis.get_majorticklocs()  # get main graduations",
            f"{axe}.{dim}axis.set_minor_locator(ticker.MultipleLocator((ticks[1]-ticks[0])/10.0))",
        ]
    msg = f"{scale} is not valid"
    raise ValueError(msg)


def print_fill_axe(**kwargs: dict) -> list[str]:
    """Return the code that fill a given axes."""
    code = [
        "def fill_axe(axe: plt.Axes, values: dict[str], ylab: str, xlab: str):",
        '    """Fill in the axis with the data provided as input."""',
    ]
    if kwargs["color"] is not None:
        code.append('    color_labels = sorted(set(values["color"]), key=smartsort)')
    if kwargs["marker"] is not None:
        code.append('    marker_labels = sorted(set(values["marker"]), key=smartsort)')
    match (kwargs["color"] is None, kwargs["marker"] is None):
        case (True, True):  # no color, no marker
            code.extend([
                "    x_data, y_data = values[xlab], values[ylab]",
                *(f"    {line}" for line in print_error(**kwargs)),
                "    axe.errorbar(",
                "        x_data, y_data,",
                "        xerr=xerr, yerr=yerr,",
                "        color=COLORS[0],",
                "        fmt=MARKERS[0],",
                "        capsize=3,",
                "        markersize=MARKERSIZE,",
                "    )",
            ])
        case (False, True):  # only color
            code.extend([
                "    for color_label, color in zip(color_labels, itertools.cycle(COLORS)):",
                '        mask = [v == color_label for v in values["color"]]',
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                "        x_data, y_data = sub_values[xlab], sub_values[ylab]",
                *(f"        {line}" for line in print_error(**kwargs)),
                "        axe.errorbar(",
                "            x_data, y_data,",
                "            xerr=xerr, yerr=yerr,",
                f'            label=f"{kwargs["color"]}={{color_label}}", ',
                "            color=color,",
                "            fmt=MARKERS[0],",
                "            capsize=3,",
                "            markersize=MARKERSIZE",
                "        )",
            ])
        case (True, False):  # only marker
            code.extend([
                "    for marker_label, marker in zip(marker_labels, itertools.cycle(MARKERS)):",
                '        mask = [v == marker_label for v in values["marker"]]',
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                "        x_data, y_data = sub_values[xlab], sub_values[ylab]",
                *(f"        {line}" for line in print_error(**kwargs)),
                "        axe.errorbar(",
                "            x_data, y_data,",
                "            xerr=xerr, yerr=yerr,",
                f'            label=f"{kwargs["marker"]}={{marker_label}}", ',
                "            color=COLORS[0],",
                "            fmt=marker,",
                "            capsize=3,",
                "            markersize=MARKERSIZE",
                "        )",
            ])
        case (False, False):  # both color and marker
            code.extend([
                "",
                "    # create legend",
                "    for color_label, color in zip(color_labels, itertools.cycle(COLORS)):",
                (
                    "        axe.errorbar("
                    f'[], [], color=color, label=f"{kwargs["color"]}={{color_label}}"'
                    ")"
                ),
                "    for marker_label, marker in zip(marker_labels, itertools.cycle(MARKERS)):",
                (
                    "        axe.errorbar("
                    '[], [], color="grey", fmt=marker, '
                    f'label=f"{kwargs["marker"]}={{marker_label}}"'
                    ")"
                ),
                "",
                "    # plot data",
                "    for (color_label, color), (marker_label, marker) in itertools.product(",
                "        zip(color_labels, itertools.cycle(COLORS)),",
                "        zip(marker_labels, itertools.cycle(MARKERS)),",
                "    ):",
                "        mask = [",
                "            vc == color_label and vm == marker_label",
                '            for vc, vm in zip(values["color"], values["marker"])',
                "        ]",
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                "        x_data, y_data = sub_values[xlab], sub_values[ylab]",
                *(f"        {line}" for line in print_error(**kwargs)),
                "        axe.errorbar(",
                "            x_data, y_data,",
                "            xerr=xerr, yerr=yerr,",
                "            color=color,",
                "            fmt=marker,",
                "            capsize=3,",
                "            markersize=MARKERSIZE",
                "        )",
            ])

    code.extend(["", ""])
    return code


def print_header() -> list[str]:
    """Return the code at the very top of the file."""
    return [
        "#!/usr/bin/env python3",
        "",
        (
            f'"""Code auto-generated by mendevi {__version__} '
            f'the {datetime.datetime.now(tz=datetime.UTC)}."""'
        ),
        "",
    ]


def print_import() -> list[str]:
    """Print the importations."""
    return [
        "import itertools",
        "import math",
        "import pathlib",
        "import sqlite3",
        "",
        "from context_verbose import Printer",
        "from mendevi.exceptions import RejectError",
        "from mendevi.plot.tools import smartsort",
        "from mendevi.utils import best_profile",
        "import cutcutcodec",
        "import matplotlib.figure as figure",
        "import matplotlib.pyplot as plt",
        "import matplotlib.ticker as ticker",
        "import mendevi.database.extract as extract",
        "import numpy as np",
        "import tqdm",
        "",
        "",
    ]


def print_subfigure(**kwargs: dict) -> list[str]:
    """Return the code for the subplot of a a given y and y axis."""
    header = [
        (
            f"def plot_{safe_lbl(kwargs['ylabel'])}_{safe_lbl(kwargs['xlabel'])}("
            "values: dict[str], subfig: figure.SubFigure"
            "):"
        ),
        f'    """Create the subchart for y={kwargs["ylabel"]} and x={kwargs["xlabel"]}."""',
    ]
    xlabel = f"x_{kwargs['x'].index(kwargs['xlabel'])}"
    ylabel = f"y_{kwargs['y'].index(kwargs['ylabel'])}"
    scale_x = get_extractor(kwargs["xlabel"], safe=True).scale
    scale_y = get_extractor(kwargs["ylabel"], safe=True).scale
    match (kwargs["window_y"] is None, kwargs["window_x"] is None):
        case (True, True):
            middle = [
                "    # create a simple figure",
                '    axe = subfig.subplots(sharex="col")  # or "all"',
                f"    fill_axe(axe, values, ylab={ylabel!r}, xlab={xlabel!r})",
                *(f"    {line}" for line in print_grid("axe", "y", scale=scale_y)),
                *(f"    {line}" for line in print_grid("axe", "x", scale=scale_x)),
            ]
        case (False, True):
            middle = [
                "    # create a 1d vertical subplot figure",
                '    all_window_y_values = sorted(set(values["window_y"]), key=smartsort)',
                "    nrows = len(all_window_y_values)",
                '    axes = subfig.subplots(nrows=nrows, squeeze=False, sharex="col")  # or "all"',
                "",
                "    # iterate over all subplots",
                "    for i, window_y_value in enumerate(all_window_y_values):",
                "        # select the correct data subset",
                '        mask = [y == window_y_value for y in values["window_y"]]',
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                f'        axes[i, 0].set_title({kwargs["window_y"]!r} f"={{window_y_value}}")',
                f"        fill_axe(axes[i, 0], sub_values, ylab={ylabel!r}, xlab={xlabel!r})",
                *(f"        {line}" for line in print_grid("axes[i, 0]", "y", scale=scale_y)),
                *(f"        {line}" for line in print_grid("axes[i, 0]", "x", scale=scale_x)),
            ]
        case (True, False):
            middle = [
                "    # create a 1d horizontal subplot figure",
                '    all_window_x_values = sorted(set(values["window_x"]), key=smartsort)',
                "    ncols = len(all_window_x_values)",
                '    axes = subfig.subplots(ncols=ncols, squeeze=False, sharey="row")  # or "all"',
                "",
                "    # iterate over all subplots",
                "    for j, window_x_value in enumerate(all_window_x_values):",
                "        # select the correct data subset",
                '        mask = [x == window_x_value for x in values["window_x"]]',
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                f'        axes[0, j].set_title({kwargs["window_x"]!r} f"={{window_x_value}}")',
                f"        fill_axe(axes[0, j], sub_values, ylab={ylabel!r}, xlab={xlabel!r})",
                *(f"        {line}" for line in print_grid("axes[0, j]", "y", scale=scale_y)),
                *(f"        {line}" for line in print_grid("axes[0, j]", "x", scale=scale_x)),
            ]
        case (False, False):  # 2d grid subplot
            middle = [
                "    # create a 2d grid subplot figure",
                '    all_window_y_values = sorted(set(values["window_y"]), key=smartsort)',
                '    all_window_x_values = sorted(set(values["window_x"]), key=smartsort)',
                "    nrows, ncols = len(all_window_y_values), len(all_window_x_values)",
                "    axes = subfig.subplots(",
                '        nrows, ncols, squeeze=False, sharex="col", sharey="row",',
                '    )  # or "all"',
                "",
                "    # iterate over all subplots",
                "    for (i, window_y_value), (j, window_x_value) in itertools.product(",
                "        enumerate(all_window_y_values), enumerate(all_window_x_values)",
                "    ):",
                "        # select the correct data subset",
                "        mask = [",
                "            y == window_y_value and x == window_x_value",
                '            for y, x in zip(values["window_y"], values["window_x"])',
                "        ]",
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                "        axes[i, j].set_title(",
                f'            {kwargs["window_y"]!r} f"={{window_y_value}}"',
                '            " & "',
                f'            {kwargs["window_x"]!r} f"={{window_x_value}}"',
                "        )",
                f"        fill_axe(axes[i, j], sub_values, ylab={ylabel!r}, xlab={xlabel!r})",
                *(f"        {line}" for line in print_grid("axes[i, j]", "y", scale=scale_y)),
                *(f"        {line}" for line in print_grid("axes[i, j]", "x", scale=scale_x)),
            ]
    end = [
        f"    subfig.supylabel({get_extractor(kwargs['ylabel'], safe=True).legend!r})",
        f"    subfig.supxlabel({get_extractor(kwargs['xlabel'], safe=True).legend!r})",
        "",
    ]
    return header + middle + end


def print_main(**kwargs: dict) -> list[str]:
    """Return the code of the function that plot the final graphic."""
    code = []
    # subplots
    for ylabel, xlabel in itertools.product(kwargs["y"], kwargs["x"]):
        code.extend(print_subfigure(**kwargs, ylabel=ylabel, xlabel=xlabel))

    # main function
    code.extend([
        "def main(values: dict[str]):",
        '    """Create the plots with matplotlib."""',
        "    # create and fill in the main figure",
        '    fig = plt.figure(layout="constrained", figsize=FIGSIZE)',
        (
            "    subfigs = fig.subfigures("
            f"nrows={len(kwargs['y'])}, ncols={len(kwargs['x'])}, squeeze=False"
            ")"
        ),
    ])
    for (i, ylabel), (j, xlabel) in itertools.product(
        enumerate(kwargs["y"]), enumerate(kwargs["x"]),
    ):
        code.extend([
            f"    plot_{safe_lbl(ylabel)}_{safe_lbl(xlabel)}(values, subfigs[{i}, {j}])",
        ])
    code.extend([
        "",
        "    axes = [a for f in subfigs.flat for a in np.ravel(f.axes)]",
        "",
        "    # adjusts the figsize according to the number of graphs",
        "    nrows = np.vectorize(",
        "        lambda s: s.axes[0].get_gridspec().nrows",
        "    )(subfigs).sum(axis=0).max()",
        "    ncols = np.vectorize(",
        "        lambda s: s.axes[0].get_gridspec().ncols",
        "    )(subfigs).sum(axis=1).max()",
        "    fig.set_size_inches(FIGSIZE[0]*math.sqrt(ncols), FIGSIZE[1]*math.sqrt(nrows))",
        "",
        "    # recompute limits to solve share log errorbar matplotlib error",
        "    for axe in axes:",
        "        axe.relim()  # recompute limits",
        "        axe.autoscale()  # adjust the view",
        "",
        "    # legend managment",
        "    labels = {frozenset(a.get_legend_handles_labels()[1]) for a in axes}",
        "    if len(axes) != 1 and len(labels) == 1:  # same legend everywhere",
        "        lines, labels = axes[0].get_legend_handles_labels()",
        "        if labels:",
        "            fig.legend(",
        '                lines, labels, loc="outside upper center", ncols=min(5, len(labels))',
        "            )",
        "    else:",
        "        for subfig in subfigs.flat:",
        "            axes = np.ravel(subfig.axes)",
        "            labels = {frozenset(a.get_legend_handles_labels()[1]) for a in axes}",
        "            if len(axes) != 1 and len(labels) == 1:  # same legend in all axes",
        "                lines, labels = axes[0].get_legend_handles_labels()",
        "                if labels:",
        "                    subfig.legend(",
        (
            "                        "
            'lines, labels, loc="outside upper center", ncols=min(3, len(labels))'
        ),
        "                    )",
        "            else:  # legends are different for each axe of that subfigure",
        "                for axe in axes:",
        "                    axe.legend(ncols=max(1, len(next(iter(labels)))//16))",
        "",
    ])
    keys = ["x", "y", "color", "marker", "window_x", "window_y", "error", "filter", "table"]
    code.extend([
        "",
        "    # save the figure",
        "    metadata = {",
        '        "Keywords": ["mendevi", "video", "encoding", "decoding"],',
        '        "Language": "en",',
        '        "Rights": "Free lisence GLPv3",',
        '        "Contributor": ["Robin RICHARD (robinechuca)"],',
        f'        "Creator": "mendevi {__version__}",',
        f'        "Description": "A plot with {", ".join(f"{k}={kwargs[k]}" for k in keys)}",',
        f'        "Title": {kwargs["path"].stem!r},',
        "    }",
        "    plt.savefig(FIGNAME, format=FIGNAME.suffix[1:], transparent=False, metadata=metadata)",
        "    plt.show()",
        "",
        "",
    ])
    return code


def print_mean_std() -> list[str]:
    """Return the code to compute the mean and the std of a list."""
    return [
        "def mean_std(data: list[float]) -> tuple[float, float]:",
        '    """Compute the mean and the unbiaised std of a list."""',
        "    data = [d for d in data if d is not None]",
        "    match nbr := float(len(data)):",
        "        case 0.0:",
        "            return math.nan, math.nan",
        "        case 1.0:",
        "           return data[0], math.nan",
        "    mean = sum(data) / nbr",
        "    if (var_sum := sum((x-mean)**2 for x in data)) == 0.0:",
        "        return mean, math.nan",
        "    std = math.sqrt(var_sum / (nbr - 1.0))",
        "    return mean, std",
        "",
        "",
    ]


def print_read_sql(**kwargs: dict) -> list[str]:
    """Return the code of the function that perform the sql request."""
    alias = {
        f"x_{i}": expr for i, expr in enumerate(kwargs["x"])
    } | {
        f"y_{i}": expr for i, expr in enumerate(kwargs["y"])
    } | {
        lbl: kwargs[lbl]
        for lbl in ["color", "marker", "window_x", "window_y", "error"]
        if kwargs[lbl] is not None
    }

    # get sql query
    atom_names, line_extractor = merge_extractors(set(alias), alias=alias, select=kwargs["filter"])
    select = {s for lbl in atom_names for s in get_extractor(lbl).func.select}
    if len(queries := SqlLinker(*select).sql) == 0:
        logging.getLogger(__name__).warning(
            "fail to create the SQL query, please provide it yourself",
        )
        queries = [""]

    # select good query
    if kwargs["table"] is not None:
        table = kwargs["table"]
        queries = {re.search(r"FROM\s+(?P<tab>\w+)", q)["tab"]: q for q in queries}
        if table not in queries:
            msg = f"possible queries from {', '.join(queries)}, not {table}"
            raise ValueError(msg)
        queries = [queries[table]]
    else:
        table = re.search(r"FROM\s+(?P<tab>\w+)", queries[0])["tab"]

    # include in template
    return [
        *line_extractor,
        "",
        "",
        "def thread_line_extractor(row: sqlite3.Row) -> dict[str] | None:",
        '    """Multiprocessing compatible version of `line_extractor`."""',
        "    assert isinstance(row, sqlite3.Row), row.__class__.__name__",
        "    row = dict(row)",
        "    try:",
        "        return line_extractor(row)",
        "    except RejectError:",
        "        return None",
        "",
        "",
        "def read_sql(database: pathlib.Path) -> dict[str, list]:",
        '    """Extract the relevant values from the database."""',
        f"    values: dict[str, list] = {{{', '.join(f'{n!r}: []' for n in sorted(alias))}}}",
        (
            '    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as conn, '
            'Printer("Read database...") as prt:'
        ),
        f'        (count,) = conn.execute("SELECT COUNT(*) FROM {table}").fetchone()',
        "        conn.row_factory = sqlite3.Row",
        "        for line in tqdm.tqdm(",
        "            cutcutcodec.core.opti.parallel.imap(",
        "                thread_line_extractor,",
        "                conn.execute(",
        '                    """',
        f"                    {'\n                    '.join(queries[0].split('\n'))}",
        '                    """',
        *[
            f"                    # {q}"
            for q in "\n".join(f'"""\n{q}\n"""' for q in queries[1:]).split("\n")
        ],
        "                ),",
        "            ),",
        "            dynamic_ncols=True,",
        "            leave=False,",
        "            smoothing=1e-6,",
        "            total=count,",
        '            unit="line",',
        "        ):",
        "            if line is not None:",
        "                for label, value in line.items():",
        "                    values[label].append(value)",
        "        prt.print_time()",
        "    return values",
        "",
        "",
    ]


def safe_lbl(lbl: str) -> str:
    """Convert the label into a valid lowercase variable."""
    assert isinstance(lbl, str), lbl.__class__.__name__
    for symb, rep in [("+", "plus"), ("-", "minus"), ("*", "times"), ("/", "per")]:
        lbl = lbl.replace(symb, f"_{rep}_")
    return re.sub(r"[^0-9a-zA-Z]+", "_", lbl.lower())
