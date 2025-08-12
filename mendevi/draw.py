#!/usr/bin/env python3

"""Draw graphs from the database."""

import click
import itertools
import json
import pathlib
import re
import typing

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np


class DynAnnot:
    """Create dynamic annotations."""

    def __call__(self, event):
        # print(event)
        # vis = annot.get_visible()
        pass


def get_floats(value: float | int | str | list | dict) -> typing.Iterable[float]:
    """Extract all the number recursively."""
    match value:
        case float():
            yield value
        case int():
            yield float(value)
        case str():
            try:
                yield float(value)
            except ValueError:
                pass
        case list() | tuple() | set() | frozenset():
            yield from (e for v in value for e in get_floats(v))
        case dict():
            yield from (e for v in value.values() for e in get_floats(v))
        case _:
            raise TypeError(f"unrecognize value {value}")


def get_float_mean(value: object) -> float:
    """Return the mean of the float, or raise ValueError."""
    if len(values := list(get_floats(value))) == 0:
        raise ValueError(f"no number found in {value}")
    return float(np.mean(values))


def get_value(value: dict | list, field: str | None) -> object:
    """Exctract the value that correspond to the given field.

    Returns None if it failed.
    """
    if field is None:
        return None
    assert isinstance(value, dict | list), value.__class__.__name__
    assert isinstance(field, str), field.__class__.__name__
    if isinstance(value, list):
        return [get_value(e, field) for e in value]
    key, *sub_keys = field.split(".")
    if (value := value.get(key, None)) is not None:
        if sub_keys:
            return get_value(value, ".".join(sub_keys))
    return value


def _log_is_better(data_lin: np.ndarray[np.float64]) -> bool:
    """Return True if the data should be plot in a log scale."""
    if data_lin.min() <= 0.0:
        return False
    if data_lin.max() / data_lin.min() < 10.0**1.5:  # minimum 1.5 decades
        return False
    data_log = np.log(data_lin)
    bins = 1 + round(len(data_lin)**0.5)
    hist_lin, _ = np.histogram(data_lin, bins=bins)
    hist_lin = (hist_lin.astype(np.float64) + np.finfo(np.float64).eps) / len(data_lin)
    hist_log, _ = np.histogram(data_log, bins=bins)
    hist_log = (hist_log.astype(np.float64) + np.finfo(np.float64).eps) / len(data_log)
    kullback_lin = -np.log(hist_lin).sum()  # rigouresly np.sum(np.log((1/bins) / hist_lin)) / bins
    kullback_log = -np.log(hist_log).sum()
    return kullback_log < kullback_lin


def _draw(axes: plt.Axes, data: dict[str: dict], values: dict[str: dict[str]]):
    """Create the plot."""
    # set title
    if (lbl := set(map(str, values["w"].values()))) != {"None"}:
        axes.set_title(", ".join(sorted(lbl)))

    # set legend
    colors_label = sorted(set(map(str, values["c"].values())))
    shapes_label = sorted(set(map(str, values["s"].values())))
    if len(colors_label) > 1:
        for i in range(len(colors_label)):
            axes.scatter([], [], color=cm.rainbow(i/(len(colors_label)-1)), label=colors_label[i], marker=1)
    if len(shapes_label) > 1:
        for j in range(len(shapes_label)):
            axes.scatter([], [], color="black", label=shapes_label[j], marker=".x^1s+Dv234<>hH"[j%15])
    if len(colors_label) > 1 or len(shapes_label) > 1:
        axes.legend()

    # draw scatter cloud
    for i, j in itertools.product(range(len(colors_label)), range(len(shapes_label))):
        x_data, y_data = zip(*(
            (values["x"][name], values["y"][name]) for name in data
            if str(values["c"][name]) == colors_label[i] and str(values["s"][name]) == shapes_label[j]
        ))
        x_data, y_data = np.asarray(x_data, dtype=np.float64), np.asarray(y_data, dtype=np.float64)
        axes.scatter(
            x_data,
            y_data,
            color=cm.rainbow(i/(len(colors_label)-1)) if len(colors_label) > 1 else None,
            marker=".x^1s+Dv234<>hH"[j%15] if len(shapes_label) > 1 else None,
        )

    # put decoration
    axes.grid()
    x_data = np.asarray(list(values["x"].values()), dtype=np.float64)
    axes.set_xscale("log" if _log_is_better(x_data) else "linear")
    y_data = np.asarray(list(values["y"].values()), dtype=np.float64)
    axes.set_yscale("log" if _log_is_better(y_data) else "linear")
    # axes.set_xlabel(kwargs["x"])
    # axes.set_ylabel(kwargs["y"])


@click.command()
@click.argument("filename", required=True, type=click.Path())
@click.option("-x", required=True, help="the field along x axis")
@click.option("-y", required=True, help="the field along y axis")
@click.option("-c", "--color", type=str, help="criteria for points color")
@click.option("-s", "--shape", type=str, help="criteria for the points shape")
@click.option("-w", "--window", type=str, help="criteria for the points window")
@click.option("-u", "--unfold", type=click.Choice(list("xycsw")), multiple=True, help="the field to unfold")
@click.option("-f", "--filter", type=str, help="criteria to be filtered")
def main(filename: str, **kwargs):
    """Draw graphs from the database.

    Parameters
    ----------
    filename : pathlike
        The name of the json file.
    x, y : str
        The name of the field to plot for the x and the y axis.
        For example ``encode_power.energy``.
    filter : str, optional
        The condition to keep the file, formatted as ``field=value``.
        For example ``encoder=libx264``
    """
    # extract the database content
    filename = pathlib.Path(filename).expanduser()
    assert filename.is_file(), f"the given file {filename} doesn't exists"
    with open(filename, "rb") as raw:
        data = json.load(raw)

    # filter
    if kwargs.get("filter", ""):
        key, *pattern = kwargs["filter"].split("=")
        pattern = "=".join(pattern)
        plt.title(f"{key} = {pattern}")
        if not (data := {
            name: values for name, values in data.items()
            if re.search(pattern, get_value(values, key) or "") is not None
        }):
            raise KeyError(f"the filter {key} = {pattern} reject everything")

    # select values
    values = {
        "x": {n: get_value(v, kwargs["x"]) for n, v in data.items()},
        "y": {n: get_value(v, kwargs["y"]) for n, v in data.items()},
        "c": {n: get_value(v, kwargs["color"]) for n, v in data.items()},
        "s": {n: get_value(v, kwargs["shape"]) for n, v in data.items()},
        "w": {n: get_value(v, kwargs["window"]) for n, v in data.items()},
    }

    # unfold values
    for field in kwargs["unfold"]:
        for name in data.copy():
            if not isinstance(values[field][name], list | tuple):
                continue
            for i in range(len(values[field][name])):
                new_name = f"x{i+1}_{name}"
                for field_ in "xycsw":
                    if isinstance(values[field_][name], list | tuple):
                        values[field_][new_name] = values[field_][name][i]
                    else:
                        values[field_][new_name] = values[field_][name]
                data[new_name] = data[name]
            del data[name]
            for field_ in "xycsw":
                del values[field_][name]

    # convert to scalar
    values["x"] = {n: get_float_mean(v) for n, v in values["x"].items()}
    values["y"] = {n: get_float_mean(v) for n, v in values["y"].items()}

    # display
    fig = plt.figure(figsize=(16, 9), dpi=None)
    fig.suptitle(filename.stem)
    dyn_annot = DynAnnot()
    windows_label = sorted(set(map(str, values["w"].values())))
    for i, lbl in enumerate(windows_label):
        axes = fig.add_subplot(1, len(windows_label), i+1)
        axes.set_xlabel(kwargs["x"])
        axes.set_ylabel(kwargs["y"])
        selected = {n for n, e in values["w"].items() if str(e) == lbl}
        _draw(
            axes,
            {n: d for n, d in data.items() if n in selected},
            {f: {n: e for n, e in v.items() if n in selected} for f, v in values.items()},
        )
    plt.tight_layout()
    lbl = " ".join(f"{k}={kwargs[k]}" for k in sorted(kwargs) if kwargs[k])
    plt.savefig(
        (pathlib.Path.cwd() / f"{filename.stem} {lbl}").with_suffix(".svg"),
        # transparent=True,
        format="svg",
    )
    fig.canvas.mpl_connect("motion_notify_event", dyn_annot)
    plt.show()


    # # display
    # fig = plt.figure()
    # ax = fig.add_subplot(111)
    # ax.set_title("Interactive MENDEVI plot")
    # scenes = []

    # if len(names := x_values.keys() & y_values.keys()) == 0:
    #     names = {k for v in data.values() for k in v}
    #     raise KeyError(f"no x={kwargs['x']} and y={kwargs['y']} label found, only {sorted(names)}")
    # names, x_data, y_data = zip(
    #     *((k, x_values[k], y_values[k]) for k in names)
    # )
    # x_data, y_data = np.asarray(x_data, np.float64), np.asarray(y_data, np.float64)
    # if "color" in kwargs:
    #     colors = autocolors()
    #     colors = {}
    #     for i, name in enumerate(names):
    #         cat = data[name].get(kwargs["color"], "not specified")
    #         colors[cat] = colors.get(cat, [])
    #         colors[cat].append(i)
    #     for cat in sorted(colors):
    #         idx = np.asarray(colors[cat], dtype=np.int64)
    #         scenes.append([ax.scatter(x_data[idx], y_data[idx], label=cat), names])
    # else:
    #     scenes.append([ax.scatter(x_data, y_data), names])

    # ax.grid()
    # ax.set_xscale("log" if _log_is_better(x_data) else "linear")
    # ax.set_yscale("log" if _log_is_better(y_data) else "linear")
    # ax.set_xlabel(kwargs["x"])
    # ax.set_ylabel(kwargs["y"])
    # plt.tight_layout()
    # if "color" in kwargs:
    #     plt.legend()

    # def update_annot(sc, ind, name):
    #     idx = ind["ind"][0]
    #     pos = sc.get_offsets()[idx]
    #     annot.xy = pos

    #     text = ""
    #     for key in ["compression_ratio", "crf", "encode_duration", "encode_threads", "encoder", "preset", "profile"]:
    #         text += f"{key}={data[name][key]}\n"
    #     text = text[:-1]
    #     annot.set_text(text)
    #     annot.get_bbox_patch().set_facecolor("lightyellow")
    #     annot.get_bbox_patch().set_alpha(0.8)

    #     # Calculer la position relative du point dans la figure
    #     x_disp, y_disp = ax.transData.transform(pos)
    #     width, height = fig.get_size_inches()*fig.dpi

    #     # Choisir un offset en fonction de l'espace autour du point
    #     offset_x = 20 if x_disp < width * 0.7 else -200  # vers la droite ou vers la gauche
    #     offset_y = 20 if y_disp < height * 0.7 else -100  # vers le haut ou le bas

    #     annot.set_position((offset_x, offset_y))

    # # Fonction appelée lors du mouvement de la souris
    # def hover(event):
    #     vis = annot.get_visible()
    #     if event.inaxes == ax:
    #         for i, (sc, names) in enumerate(scenes):
    #             cont, ind = sc.contains(event)
    #             if cont:
    #                 update_annot(sc, ind, names[i])
    #                 annot.set_visible(True)
    #                 fig.canvas.draw_idle()
    #                 break
    #             elif vis:
    #                 annot.set_visible(False)
    #                 fig.canvas.draw_idle()
    # annot = ax.annotate(
    #     "",
    #     xy=(0, 0),
    #     xytext=(10, 10),
    #     textcoords="offset points",
    #     bbox=dict(boxstyle="round", fc="w"),
    #     arrowprops=dict(arrowstyle="->"),
    # )
    # annot.set_visible(False)
    # fig.canvas.mpl_connect("motion_notify_event", hover)
    # plt.show()
