# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Few tools to help display."""

import functools
import numbers

import matplotlib.pyplot as plt
from matplotlib import ticker

from mendevi.cst.profiles import PROFILES


@functools.cache
def sorted_profiles() -> dict[str, int]:
    """Sort the profiles."""
    profiles = sorted(
        PROFILES, key=lambda p: PROFILES[p]["resolution"][0]*PROFILES[p]["resolution"][1],
    )
    return dict(zip(profiles, range(len(profiles)), strict=True))


def smartsort(item: object) -> object:
    """Make the order relationship more relevant."""
    if isinstance(item, str):
        profiles = sorted_profiles()
        efforts = {"fast": 0, "medium": 1, "slow": 2}  # optional for now because already ordered
        return {**profiles, **efforts}.get(item, item)
    if isinstance(item, numbers.Real):
        return item
    return str(item)


def lin_grid(axe: plt.Axes, axis: str) -> plt.Axes:
    """Set a linear grid on the given axis."""
    assert isinstance(axe, plt.Axes), axe.__class__.__name__
    assert isinstance(axis, str), axis.__class__.__name__
    match axis:
        case "x":
            axe.set_xscale("linear")
            axe.grid(axis=axis, which="major")
            axe.grid(axis=axis, which="minor", color="0.9")
            ticks = axe.xaxis.get_majorticklocs()  # get main graduations
            axe.xaxis.set_minor_locator(ticker.MultipleLocator((ticks[1]-ticks[0])/10.0))
        case "y":
            axe.set_yscale("linear")
            axe.grid(axis=axis, which="major")
            axe.grid(axis=axis, which="minor", color="0.9")
            ticks = axe.yaxis.get_majorticklocs()  # get main graduations
            axe.yaxis.set_minor_locator(ticker.MultipleLocator((ticks[1]-ticks[0])/10.0))
        case _:
            msg = f"'axe' can only take the values 'x' or 'y', not {axe}"
            raise ValueError(msg)
    return axe


def log_grid(axe: plt.Axes, axis: str) -> plt.Axes:
    """Set a log grid on the given axis."""
    assert isinstance(axe, plt.Axes), axe.__class__.__name__
    assert isinstance(axis, str), axis.__class__.__name__
    match axis:
        case "x":
            axe.set_xscale("log", base=10)
        case "y":
            axe.set_yscale("log", base=10)
        case _:
            msg = f"'axe' can only take the values 'x' or 'y', not {axe}"
            raise ValueError(msg)
    axe.grid(axis=axis, which="major")
    axe.grid(axis=axis, which="minor", color="0.9")
    return axe


