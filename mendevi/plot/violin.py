# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Used to visualise the reliability of models through violin-moustache-box chart."""

import math
import typing

import torch
from matplotlib import figure, ticker

from mendevi.cst.plot import COLORS
from mendevi.models.base import Model


def fill_violin(
    models: typing.Iterable[Model],
    fig: figure.Figure | figure.SubFigure,
) -> None:
    """Plot the model validation histograms, including moustache charts.

    Parameters
    ----------
    models : list[Model]
        There will be one model per row to compare.
    fig : matplotlib figure
        The matplotlib figure in which the axes will be created.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> from mendevi.models.lr import LR
    >>> from mendevi.plot.violin import fill_violin
    >>> model_1 = LR(
    ...     input_labels=["quality"], output_labels=["psnr"],
    ... ).fit("x264_vs_openh264.db", table="t_enc_encode")
    >>> model_2 = LR(
    ...     input_labels=["height", "width"], output_labels=["psnr"],
    ... ).fit("x264_vs_openh264.db", table="t_enc_encode")
    >>> model_1.validate("x264_vs_openh264.db", table="t_enc_encode")
    >>> model_2.validate("x264_vs_openh264.db", table="t_enc_encode")
    >>> fig = plt.figure(layout="constrained")
    >>> fill_violin([model_1, model_2], fig)
    >>> plt.show()  # doctest: +SKIP
    >>>

    """
    # verifications
    assert hasattr(models, "__iter__"), models.__class__.__name__
    assert all(isinstance(m, Model) for m in models), models
    assert isinstance(fig, figure.Figure | figure.SubFigure), fig.__class__.__name__

    # find context
    output_labels = sorted({lbl for model in models for lbl in model.output_labels})
    axes = fig.subplots(
        len(models),  # nrows
        len(output_labels),  # ncols
        squeeze=False,
        sharex="all",
        sharey="col",
    )

    # compute all mapes
    mapes = [[None for _ in output_labels] for _ in models]
    for i, model in enumerate(models):
        for j, output_label in enumerate(output_labels):
            # compute mape
            pred, val = torch.cat([clus[output_label] for clus in model.accuracy.values()], dim=1)
            if output_label.startswith("log_"):
                pred, val = 10.0**pred, 10.0**val
            mape = ((val - pred).abs() / (val.abs() + torch.finfo(torch.float32).eps)).mean(dim=1)
            mapes[i][j] = mape

    # fill each axe
    for i, model in enumerate(models):
        for j, output_label in enumerate(output_labels):
            # prepare data
            bins = math.ceil(math.sqrt(len(mapes[i][j]))) + 1
            maxi = max(torch.quantile(mape[j], .95) for mape in mapes)
            hist = torch.histc(mapes[i][j], bins=bins, min=0)#, max=maxi)
            hist /= hist.max()
            quants = torch.quantile(mapes[i][j], torch.asarray([0.05, 0.25, 0.5, 0.75, 0.95]))

            # plot
            axes[i, j].set_yticks([])  # no graduations on vertical axis
            axes[i, j].xaxis.set_major_formatter(ticker.PercentFormatter(1))
            axes[i, j].set_xlim(0, maxi)
            axes[i, j].set_xlabel(output_label, loc="center")
            axes[i, j].xaxis.set_label_position("top")
            axes[i, j].set_ylabel(model.title, loc="center")
            axes[i, j].yaxis.set_label_position("left")

            # draw histogram then moustache-box
            axes[i, j].bar(
                [quants[1]], [1],
                width=quants[2]-quants[1], align="edge", color=COLORS[0], label="second quartile",
            )
            axes[i, j].bar(
                [quants[2]], [1],
                width=quants[3]-quants[2], align="edge", color=COLORS[1], label="third quartile",
            )
            axes[i, j].bar(
                torch.linspace(0, (maxi / bins)*(bins-1), bins), hist,
                width=maxi / bins, align="edge", color=COLORS[2], label="histogram",
            )
            axes[i, j].plot(
                [[quants[0], quants[1], quants[2], quants[3], quants[4]],
                 [quants[0], quants[1], quants[2], quants[3], quants[4]]],
                [[.75, 1, 1, 1, .75],
                 [.25, 0, 0, 0, .25]],
                color=COLORS[4],
            )
            axes[i, j].plot(
                [[quants[0], quants[1], quants[1], quants[3]],
                 [quants[1], quants[3], quants[3], quants[4]]],
                [[.5, 1, 0, .5],
                 [.5, 1, 0, .5]],
                color=COLORS[4],
            )

    # context
    lines, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(lines, labels, loc="outside upper center", ncols=3)
    fig.supxlabel("Absolute Percentage Error")
