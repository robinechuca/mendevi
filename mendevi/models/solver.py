# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Use a model to solve an optimization problem."""

import itertools
import pathlib
import shlex
import tempfile
import typing

from context_verbose import Printer

from mendevi.cmd import CmdFFMPEG
from mendevi.cst.encoders import ENCODERS
from mendevi.cst.profiles import PROFILES
from mendevi.cst.threads import THREADS
from mendevi.encode import get_transcode_cmd
from mendevi.utils import get_pix_fmt

from .base import Model

N_QUAL: int = 24  # default number of tested quality points
DEFAULT_GRID: dict[str, list] = {
    "effort": ["fast", "medium", "slow"],
    "encoder": sorted(ENCODERS),
    "mode": ["crf", "cbr"],
    "profile": sorted(PROFILES),
    "quality": [i/(N_QUAL+2) for i in range(1, N_QUAL+2)],
    "threads": [THREADS],
}


class Solver:
    """Minimizes a metric for a given model.

    Performs a grid search on all free parameters.

    Examples
    --------
    >>> import cutcutcodec
    >>> from mendevi.models import Solver
    >>> from mendevi.models.lr import EncodeLinear
    >>> model = EncodeLinear().fit("x264_vs_openh264.db", table="t_enc_encode")
    >>> solver = Solver(model, lambda **kwd: kwd["log_energy_per_frame"] + (kwd["psnr"]-35)**2)
    >>> video = cutcutcodec.utils.get_project_root() / "media" / "video" / "intro.webm"
    >>> tested_combinations, loss = solver.solve(video, encoder=["libopenh264", "libx264"])
    >>>

    """

    def __init__(
        self, model: Model, loss: typing.Callable, grid: dict[str, list] | None = None,
    ) -> None:
        """Prepare the solver.

        Parameters
        ----------
        model : :py:class:`mendevi.models.base.Model`
            The instantiated and fitted model, ready to be evaluated.
        loss : callable
            The cost function, which takes the value of the labels as input and returns a scalar.
        grid : dict[str, list], optional
            Allows you to define the list of values to be tested.
            It is a dictionary that for each input label, associate the values to be tested.

        """
        # input verifications
        assert isinstance(model, Model), \
            f"you must to provide a model, not {model.__class__.__name__}"
        assert model.is_fit(), "the model has not been trained, you must first call the fit method."
        assert callable(loss), loss.__class__.__name__
        grid = grid or {}
        assert isinstance(grid, dict), grid.__class__.__name__
        assert all(k in model.input_labels for k in grid), (sorted(grid), model.input_labels)
        assert all(isinstance(v, list) for v in grid.values()), grid
        self._model = model
        self._loss = loss

        # set parameters for the grid search
        self._grid: dict[str, list] = {}  # for each input label, associate the values to be tested
        for label in self._model.input_labels:
            if label in grid:
                self._grid[label] = grid[label]
            elif label in DEFAULT_GRID:
                self._grid[label] = DEFAULT_GRID[label]

    @staticmethod
    def _enc_cmd(video: pathlib.Path, values: dict[str, list]) -> CmdFFMPEG | None:
        """To each point, return the ffmpeg encode command."""
        keys = list(values)
        if not {"encoder", "mode", "quality"}.issubset(keys) or video is None:
            return  # reject not encoding cases

        dst = pathlib.Path(tempfile.gettempdir()) / f"{video.stem}_optimal.mp4"
        for point_tuple in zip(*(values[k] for k in values), strict=True):
            point = dict(zip(keys, point_tuple, strict=True))
            kwargs = {
                "encoder": point["encoder"],
                "mode": point["mode"],
                "quality": point["quality"],
                "effort": point.get("effort", "medium"),
                "threads": point.get("threads", THREADS),
                "filter": point.get("filter"),
                "fps": point.get("fps"),
                "resolution": point.get(
                    "resolution",
                    (
                        (point["height"], point["width"])
                        if "height" in point and "width" in point else
                        None
                    ),
                ),
                "pix_fmt": point.get("pix_fmt", get_pix_fmt(video)),
            }
            cmd = get_transcode_cmd(video, dst, **kwargs)
            cmd.output = ["-map", "0:v:0", *cmd.output]
            yield cmd

    def solve(
        self, video: pathlib.Path | str | None = None, **kwargs: dict[str],
    ) -> tuple[dict[str, list], list[float]]:
        """Test all combinations as a cartesian product.

        Parameters
        ----------
        video : pathlike, optional
            Use this to extract the missing parameters.
        **kwargs : dict, optional
            Use to define or redefine certain input parameters to be explored.
            Explore the cartesian product of all the values.

        Returns
        -------
        values : dict[str, list]
            Associate the list of provided and predicted values with each label, input and output.
        loss : list[float]
            The value of the stroke function for each point.
            This list is sorted in ascending order.

        """
        with Printer("Solve...", color="pink") as prt:

            # preparation of cartesian product of input parameters
            if video is not None:
                kwargs = {**self._model.extract_video_props(video), **kwargs}
            kwargs = self._model.vectorize_kwargs({**self._grid, **kwargs}, _skip_duplication=True)
            keys = sorted(kwargs)  # for repetability
            values = dict(
                zip(
                    keys,
                    zip(*itertools.product(*(kwargs[k] for k in keys)), strict=True),
                    strict=True,
                ),
            )

            # predictions
            values |= self._model.predict(**values)
            keys = sorted(values)

            # compute loss
            loss = [
                self._loss(**dict(zip(keys, p, strict=True)))
                for p in zip(*(values[k] for k in keys), strict=True)
            ]

            # sort
            idx = sorted(range(len(loss)), key=loss.__getitem__)
            values = {k: [v[i] for i in idx] for k, v in values.items()}
            loss = [loss[i] for i in idx]

            # display
            with Printer(f"Result for loss = {loss[0]:#.4g}:", color="green"):
                lbl_len = max(map(len, values))
                for lbl in sorted(keys):
                    std = ""
                    if lbl in self._model.accuracy:
                        std = f" \u00B1 {self._model.accuracy[lbl]:#.4g}{std}"
                    if isinstance(values[lbl][0], float):
                        prt.print(f"{lbl:<{lbl_len}}: {values[lbl][0]:#.4g}{std}")
                    else:
                        prt.print(f"{lbl:<{lbl_len}}: {values[lbl][0]}{std}")
            try:
                cmd = next(iter(self._enc_cmd(video, values)))
            except StopIteration:
                pass
            else:
                prt.print(cmd)
                prt.print(
                    f"mendevi probe {shlex.quote(str(cmd.output[-1]))} "
                    f"-r {shlex.quote(str(video))} -d /tmp/solver.db",
                )

        return values, loss
