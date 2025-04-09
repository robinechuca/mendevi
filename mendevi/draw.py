#!/usr/bin/env python3

"""Draw graphs from the database."""

import click
import json
import pathlib
import re
import typing

import matplotlib.pyplot as plt
import numpy as np


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
        case list():
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


def get_value(value: dict | list, field: str) -> object:
    """Exctract the value that correspond to the given field.

    Returns None if it failed.
    """
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
    if data_lin.max() / data_lin.min() < 10:  # minimum one decade
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


@click.command()
@click.argument("filename", required=True, type=click.Path())
@click.option("-x", required=True, help="the field along x axis")
@click.option("-y", required=True, help="the field along y axis")
@click.option("-c", "--color", type=str, help="criteria for coloring curves")
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

    # select x
    x_values = {}
    for name, values in data.items():
        if (value := get_value(values, kwargs["x"])) is None:
            continue
        x_values[name] = get_float_mean(value)

    # select y
    y_values = {}
    for name, values in data.items():
        if (value := get_value(values, kwargs["y"])) is None:
            continue
        y_values[name] = get_float_mean(value)

    # display
    if len(names := x_values.keys() & y_values.keys()) == 0:
        names = {k for v in data.values() for k in v}
        raise KeyError(f"no x={kwargs['x']} and y={kwargs['y']} label found, only {sorted(names)}")
    names, x_data, y_data = zip(
        *((k, x_values[k], y_values[k]) for k in names)
    )
    x_data, y_data = np.asarray(x_data, np.float64), np.asarray(y_data, np.float64)
    if "color" in kwargs:
        colors = {}
        for i, name in enumerate(names):
            cat = data[name].get(kwargs["color"], "not specified")
            colors[cat] = colors.get(cat, [])
            colors[cat].append(i)
        for cat in sorted(colors):
            idx = np.asarray(colors[cat], dtype=np.int64)
            plt.scatter(x_data[idx], y_data[idx], label=cat)
    else:
        plt.scatter(x_data, y_data)

    plt.grid()
    if _log_is_better(x_data):
        plt.xscale("log")
    if _log_is_better(y_data):
        plt.yscale("log")
    plt.xlabel(kwargs["x"])
    plt.ylabel(kwargs["y"])
    plt.tight_layout()
    if "color" in kwargs:
        plt.legend()
    plt.show()
