#!/usr/bin/env python3

"""Generate a Python code that allows you to plot the graph."""

import ast
import datetime
import itertools
import logging

from mendevi import __version__
from mendevi.database.extract import SqlLinker
from mendevi.database.meta import get_extractor


def printer(**kwargs) -> str:
    """Create an excecutable python code.

    Parameters
    ----------
    database : pathlib.Path
        The database path.
    x, y : tuple[str]
        The name of the var along each axis.
    """
    # create code
    code: list[str] = []
    code.extend(print_header())
    code.extend(print_import())
    code.extend(print_cst(**kwargs))
    if kwargs["filter"] is not None:
        code.extend(print_selector(**kwargs))
    code.extend(print_read_sql(**kwargs))
    code.extend(print_fill_axe(**kwargs))
    code.extend(print_main(**kwargs))
    code.extend(print_entry())
    code = "\n".join(code)

    # format code
    try:
        import black
    except ImportError:
        logging.warning("failed to import black, please install it (uv pip install black)")
    else:
        code = black.format_str(code, mode=black.FileMode(line_length=100))
    return code


def print_entry() -> list[str]:
    """Return the code of the entry point."""
    return [
        'if __name__ == "__main__":',
        "    values: dict[str] = read_sql(DATABASE)",
        "    main(values)",
        "",
    ]


def print_cst(**kwargs) -> list[str]:
    """Return the code of the definition of the constants."""
    return [
        'COLORS = ["#ef597b", "#29a2c6", "#ffcb18", "#73b66b", "#4e4f4b"]',
        f"DATABASE = pathlib.Path({str(kwargs['database'])!r})",
        'FIGNAME = pathlib.Path(__file__).with_suffix(".svg")',
        "FIGSIZE = (10, 8)  # (width, height)",
        'MARKERS = ["o", "x", "+", "^", "d", "s", "v", "*", "D"]  # list of dot shapes',
        "MARKERSIZE = 4",
        "",
        "",
    ]


def print_grid(axe: str, log: bool | None, dim: str) -> list[str]:
    """Define the ticks rule and log or linear scale.

    Parameters
    ----------
    axe : str
        The acessor to the matplotlib axe.
    log : boolean or None
        Defined by get_extractor.
    dim : str
        "x" or "y".
    """
    assert isinstance(axe, str), axe.__class__.__name__
    assert log in {True, False, None}, log
    assert dim in {"x", "y"}, dim

    if log is None:
        logging.warning("the axis %s should be display as bar plot", dim)
        return []
    if log:
        return [
            f'{axe}.set_{dim}scale("log", base=10)  # or .set_{dim}scale("linear")',
            f'{axe}.grid(axis="{dim}", which="major")',
            f'{axe}.grid(axis="{dim}", which="minor", color="0.9")',
        ]
    return [
        f'{axe}.set_{dim}scale("linear")  # or .set_{dim}scale("log", base=10)',
        f'{axe}.grid(axis="{dim}", which="major")',
        f'{axe}.grid(axis="{dim}", which="minor", color="0.9")',
        f"ticks = {axe}.{dim}axis.get_majorticklocs()  # get main graduations",
        f"{axe}.{dim}axis.set_minor_locator(ticker.MultipleLocator((ticks[1]-ticks[0])/10.0))",
    ]


def print_fill_axe(**kwargs) -> list[str]:
    """Return the code that fill a given axes."""
    code = [
        "def fill_axe(axe: plt.Axes, values: dict[str], ylab: str, xlab: str):",
        '    """Fill in the axis with the data provided as input."""',
    ]
    if kwargs["color"] is not None:
        code.append(f"    color_labels = sorted(set(values[{kwargs['color']!r}]), key=smartsort)")
    if kwargs["marker"] is not None:
        code.append(f"    marker_labels = sorted(set(values[{kwargs['marker']!r}]), key=smartsort)")
    match (kwargs["color"] is None, kwargs["marker"] is None):
        case (True, True):  # no color, no marker
            code.extend([
                "    x_data, y_data = values[xlab], values[ylab]",
                "    axe.errorbar(",
                "        x_data, y_data,",
                "        color=COLORS[0],",
                "        fmt=MARKERS[0],",
                "        capsize=3,",
                "        markersize=MARKERSIZE,",
                "    )",
            ])
        case (False, True):  # only color
            code.extend([
                "    for color_label, color in zip(color_labels, itertools.cycle(COLORS)):",
                f"        mask = [v == color_label for v in values[{kwargs['color']!r}]]",
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                "        x_data, y_data = sub_values[xlab], sub_values[ylab]",
                "        axe.errorbar(",
                "            x_data, y_data,",
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
                f"        mask = [v == marker_label for v in values[{kwargs['marker']!r}]]",
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                "        x_data, y_data = sub_values[xlab], sub_values[ylab]",
                "        axe.errorbar(",
                "            x_data, y_data,",
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
                    '[], [], color="black", fmt=marker, '
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
                (
                    "            for vc, vm in zip("
                    f"values[{kwargs['color']!r}], values[{kwargs['marker']!r}]"
                    ")"
                ),
                "        ]",
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                "        x_data, y_data = sub_values[xlab], sub_values[ylab]",
                "        axe.errorbar(",
                "            x_data, y_data,",
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
        f'"""Code auto-generated by mendevi {__version__} the {datetime.datetime.now()}."""',
        "",
    ]


def print_import() -> list[str]:
    """Print the importations."""
    return [
        "import itertools",
        "import pathlib",
        "import sqlite3",
        "",
        "from mendevi.plot.tools import smartsort",
        "import matplotlib.figure as figure",
        "import matplotlib.pyplot as plt",
        "import matplotlib.ticker as ticker",
        "import mendevi.database.extract as extract",
        ""
        "import numpy as np",
        "",
        "",
    ]


def print_selector(**kwargs) -> list[str]:
    """Return the code for selecting a subset of the data."""
    names = sorted(
        {
            n.id
            for n in ast.walk(ast.parse(kwargs["filter"], mode="eval"))
            if isinstance(n, ast.Name)
        }
    )
    if len(names) == 1:
        loop = f"    for {names[0]} in values[{names[0]!r}]:"
    else:
        loop = f"    for {', '.join(names)} in zip({', '.join(f'values[{n!r}]' for n in names)}):"
    return [
        "def select(values: dict[str]) -> dict[str]:",
        '    """Keep only some of the data."""',
        "    mask: list[bool] = []",
        loop,
        f"        mask.append(bool({kwargs['filter']}))",
        "    values = {k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()}",
        "    return values",
        "",
        "",
    ]


def print_subfigure(**kwargs) -> list[str]:
    """Return the code for the subplot of a a given y and y axis."""
    header = [
        (
            f"def plot_{kwargs['ylabel']}_{kwargs['xlabel']}("
            "values: dict[str], subfig: figure.SubFigure"
            "):"
        ),
        f'    """Create the subchart for y={kwargs["ylabel"]} and x={kwargs["xlabel"]}."""',
    ]
    log_x = get_extractor(kwargs["xlabel"]).is_log
    log_y = get_extractor(kwargs["ylabel"]).is_log
    match (kwargs["window_y"] is None, kwargs["window_x"] is None):
        case (True, True):
            middle = [
                "    # create a simple figure",
                '    axe = subfig.subplots(sharex="col")  # or "all"',
                f"    fill_axe(axe, values, ylab={kwargs['ylabel']!r}, xlab={kwargs['xlabel']!r})",
                *(f"    {line}" for line in print_grid("axe", log_y, "y")),
                *(f"    {line}" for line in print_grid("axe", log_x, "x")),
            ]
        case (False, True):
            middle = [
                "    # create a 1d vertical subplot figure",
                f"    all_{kwargs['window_y']}_values = sorted(",
                f"        set(values[{kwargs['window_y']!r}]), ",
                "        key=smartsort,",
                "    )",
                f"    nrows = len(all_{kwargs['window_y']}_values)",
                '    axes = subfig.subplots(nrows=nrows, squeeze=False, sharex="col")  # or "all"',
                "",
                "    # iterate over all subplots",
                (
                    f"    for i, {kwargs['window_y']}_value "
                    f"in enumerate(all_{kwargs['window_y']}_values):"
                ),
                "        # select the correct data subset",
                "        mask = [",
                f"            y == {kwargs['window_y']}_value ",
                f"            for y in values[{kwargs['window_y']!r}]",
                "        ]",
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                f"        axes[i, 0].set_title({kwargs['window_y']}_value)",
                "        fill_axe(",
                "            axes[i, 0], ",
                "            sub_values, ",
                f"            ylab={kwargs['ylabel']!r}, ",
                f"            xlab={kwargs['xlabel']!r},",
                "        )",
                *(f"        {line}" for line in print_grid("axes[i, 0]", log_y, "y")),
                *(f"        {line}" for line in print_grid("axes[i, 0]", log_x, "x")),
            ]
        case (True, False):
            middle = [
                "    # create a 1d horizontal subplot figure",
                f"    all_{kwargs['window_x']}_values = sorted("
                f"        set(values[{kwargs['window_x']!r}]), ",
                "        key=smartsort,",
                "    )",
                f"    ncols = len(all_{kwargs['window_x']}_values)",
                '    axes = subfig.subplots(ncols=ncols, squeeze=False, sharey="row")  # or "all"',
                "",
                "    # iterate over all subplots",
                (
                    f"    for j, {kwargs['window_x']}_value "
                    f"in enumerate(all_{kwargs['window_x']}_values):"
                ),
                "        # select the correct data subset",
                "        mask = [",
                f"            x == {kwargs['window_x']}_value ",
                f"            for x in values[{kwargs['window_x']!r}]",
                "        ]",
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                f"        axes[0, j].set_title({kwargs['window_x']}_value)",
                "        fill_axe(",
                "            axes[0, j], ",
                "            sub_values, ",
                f"            ylab={kwargs['ylabel']!r}, ",
                f"            xlab={kwargs['xlabel']!r},",
                "        )",
                *(f"        {line}" for line in print_grid("axes[0, j]", log_y, "y")),
                *(f"        {line}" for line in print_grid("axes[0, j]", log_x, "x")),
            ]
        case (False, False):  # 2d grid subplot
            middle = [
                "    # create a 2d grid subplot figure",
                f"    all_{kwargs['window_y']}_values = sorted(",
                f"        set(values[{kwargs['window_y']!r}]), ",
                "        key=smartsort,",
                "    )",
                f"    all_{kwargs['window_x']}_values = sorted(",
                f"        set(values[{kwargs['window_x']!r}]), ",
                "        key=smartsort,",
                "    )",
                (
                    "    nrows, ncols = "
                    f"len(all_{kwargs['window_y']}_values), len(all_{kwargs['window_x']}_values)"
                ),
                "    axes = subfig.subplots(",
                '        nrows, ncols, squeeze=False, sharex="col", sharey="row",',
                '    )  # or "all"',
                "",
                "    # iterate over all subplots",
                (
                    f"    for (i, {kwargs['window_y']}_value), (j, {kwargs['window_x']}_value) "
                    "in itertools.product("
                ),
                (
                    f"        enumerate(all_{kwargs['window_y']}_values), "
                    f"enumerate(all_{kwargs['window_x']}_values)"
                ),
                "    ):",
                "        # select the correct data subset",
                "        mask = [",
                f"            y == {kwargs['window_y']}_value and x == {kwargs['window_x']}_value",
                "            for y, x in zip(",
                f"               values[{kwargs['window_y']!r}], values[{kwargs['window_x']!r}]",
                "            )",
                "        ]",
                "        sub_values = {",
                "            k: [v for v, m in zip(vs, mask) if m] for k, vs in values.items()",
                "        }",
                "        axes[i, j].set_title(",
                f"            f'{{{kwargs['window_y']}_value}} {{{kwargs['window_x']}_value}}'",
                "        )",
                (
                    "        fill_axe("
                    f"axes[i, j], sub_values, ylab={kwargs['ylabel']!r}, xlab={kwargs['xlabel']!r}"
                    ")"
                ),
                *(f"        {line}" for line in print_grid("axes[i, j]", log_y, "y")),
                *(f"        {line}" for line in print_grid("axes[i, j]", log_x, "x")),
            ]
    end = [
        f"    subfig.supylabel({get_extractor(kwargs['ylabel']).label!r})",
        f"    subfig.supxlabel({get_extractor(kwargs['xlabel']).label!r})",
        "",
    ]
    return header + middle + end


def print_main(**kwargs) -> list[str]:
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
        enumerate(kwargs["y"]), enumerate(kwargs["x"])
    ):
        code.extend([
            f"    plot_{ylabel}_{xlabel}(values, subfigs[{i}, {j}])",
        ])
    code.extend([
        "",
        "    # legend managment",
        "    axes = [a for f in np.ravel(subfigs) for a in np.ravel(f.axes)]",
        "    labels = {frozenset(a.get_legend_handles_labels()[1]) for a in axes}",
        "    if len(labels) == 1:  # legends are the same in all axes of all subfigures",
        "        lines, labels = axes[0].get_legend_handles_labels()",
        "        if labels:",
        "            fig.legend(",
        '                lines, labels, loc="outside upper center", ncols=min(5, len(labels))',
        "            )",
        "    else:",
        '        for subfig in np.ravel(subfigs):',
        '            axes = np.ravel(subfig.axes)',
        '            labels = {frozenset(a.get_legend_handles_labels()[1]) for a in axes}',
        '            if len(labels) == 1:  # legends are the same in all axes of that subfigure',
        '                lines, labels = axes[0].get_legend_handles_labels()',
        "                if labels:",
        '                    subfig.legend(',
        (
            "                        "
            'lines, labels, loc="outside upper center", ncols=min(3, len(labels))'
        ),
        "                    )",
        '            else:  # legends are different for each axe of that subfigure',
        '                for axe in axes:',
        '                    axe.legend()',
        "",
    ])
    code.extend([
        "",
        "    # save the figure",
        "    plt.savefig(FIGNAME, format=FIGNAME.suffix[1:])",
        "    plt.show()",
        "",
        "",
    ])
    return code


def print_read_sql(**kwargs) -> list[str]:
    """Return the code of the function that perform the sql request."""
    names = set(kwargs["x"]) | set(kwargs["y"])
    if kwargs["color"] is not None:
        names.add(kwargs["color"])
    if kwargs["marker"] is not None:
        names.add(kwargs["marker"])
    if kwargs["window_x"] is not None:
        names.add(kwargs["window_x"])
    if kwargs["window_y"] is not None:
        names.add(kwargs["window_y"])
    if kwargs["filter"] is not None:
        names |= {
            n.id
            for n in ast.walk(ast.parse(kwargs["filter"], mode="eval"))
            if isinstance(n, ast.Name)
        }
    names = sorted(names)

    # get sql query
    funcs = {n: get_extractor(n).func for n in names}
    select = {s for f in funcs.values() for s in f.select}
    if len(queries := SqlLinker(*select).sql) == 0:
        logging.warning("fail to create the SQL query, please provide it yourself")
        queries = [""]

    # selector
    selector = [] if kwargs["filter"] is None else ["    values = select(values)"]

    # include in template
    extract = (f"values[{n!r}].append(extract.{funcs[n].__name__}(raw))" for n in names)
    return [
        "def read_sql(database: pathlib.Path) -> dict[str, list]:",
        '    """Extract the relevant values from the database."""',
        f"    values: dict[str, list] = {{{', '.join(f'{n!r}: []' for n in names)}}}",
        "    with sqlite3.connect(database) as conn:",
        "        conn.row_factory = sqlite3.Row",
        "        for raw in conn.execute(",
        '            """',
        f"            {'\n            '.join(queries[0].split('\n'))}",
        '            """',
        *[
            f"            # {q}"
            for q in "\n".join(f'"""\n{q}\n"""' for q in queries[1:]).split("\n")
        ],
        "        ):",
        "            raw = dict(raw)",
        f"            {'\n            '.join(extract)}",
        *selector,
        "    return values",
        "",
        "",
    ]
