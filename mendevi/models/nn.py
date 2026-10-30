# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Predict the energy and the quality based on a neuronal network."""

import pathlib

import torch
import tqdm

from .base import Model


class _TorchNN(torch.nn.Module):
    """Simple perceptron nn.

    Examples
    --------
    >>> from mendevi.models.nn import _TorchNN
    >>> _TorchNN(5, 2, 1234)  # doctest: +ELLIPSIS
    _TorchNN(
      (linear): Sequential(
        (0): Linear(in_features=5, out_features=16, bias=True)
        (1): ELU(alpha=1.0)
        (2): Linear(in_features=16, out_features=32, bias=False)
        (3): BatchNorm1d(32, eps=1e-05, momentum=0.1, affine=True, ...)
        (4): ELU(alpha=1.0)
        (5): Linear(in_features=32, out_features=16, bias=True)
        (6): ELU(alpha=1.0)
        (7): Linear(in_features=16, out_features=2, bias=True)
      )
    )
    >>> _.total  # real total weight
    1234
    >>>

    """

    def __init__(self, in_ndim: int, out_ndim: int, total: int) -> None:
        # verifications
        assert isinstance(total, int), total.__class__.__name__
        total = max(total, self.minimum_size(in_ndim, out_ndim))
        super().__init__()
        torch.manual_seed(0)  # for reproductibility
        # solve total = 4*fact**2 + (in_ndim + out_ndim + 6)*fact + out_ndim
        delta = (in_ndim + out_ndim + 6)**2 - 16*(out_ndim - total)
        fact = (-(in_ndim + out_ndim + 6) + delta**.5) / 8
        fact = round(fact)
        # 4 full connected layers (better without dropout)
        self.linear = torch.nn.Sequential(
            # in_ndim * fact + fact parameters
            torch.nn.Linear(in_ndim, fact),
            torch.nn.ELU(),

            # fact * 2*fact + 2*fact + 2*fact parameters
            torch.nn.Linear(fact, 2*fact, bias=False),
            torch.nn.BatchNorm1d(2*fact),  # just this batch norm, no more
            torch.nn.ELU(),

            # 2*fact * fact + fact parameters
            torch.nn.Linear(2*fact, fact),
            torch.nn.ELU(),

            # fact * out_ndim + out_ndim parameters
            torch.nn.Linear(fact, out_ndim),
        )

        self._load_name: str = ""

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        """Inference of the vectorised model.

        Parameters
        ----------
        values : torch.Tensor
            The concatenated values of shape (batch, in_ndim)

        """
        assert isinstance(values, torch.Tensor), values.__class__.__name__
        assert values.ndim == 2, values.shape
        return self.linear(values)

    def minimum_size(self, in_ndim: int, out_ndim: int) -> int:
        """Return the minimum number of parameters."""
        assert isinstance(in_ndim, int), in_ndim.__class__.__name__
        assert in_ndim >= 1, in_ndim
        assert isinstance(out_ndim, int), out_ndim.__class__.__name__
        assert out_ndim >= 1, out_ndim
        # replace total expression (in __init__) with fact = 1
        return 10 + in_ndim + 2*out_ndim

    def load(self, name: str) -> None:
        """If exists, load the weights."""
        assert isinstance(name, str), name.__class__.__name__
        self._load_name = name
        cachedir = pathlib.Path.home() / ".cache" / "mendevi"
        weights = (cachedir / name).with_suffix(".pk.xz")
        if weights.exists():
            self.__dict__ = Model.load(weights).__dict__

    def save(self, name: str="") -> None:
        """Save the model by freezing its current state."""
        assert isinstance(name, str), name.__class__.__name__
        name = name or self._load_name
        assert name, name
        cachedir = pathlib.Path.home() / ".cache" / "mendevi"
        cachedir.mkdir(mode=0o777, parents=True, exist_ok=True)
        weights = (cachedir / name).with_suffix(".pk.xz")
        Model.save(self, weights)

    @property
    def total(self) -> int:
        """The real number of parameters."""
        return sum(p.numel() for p in self.parameters())


class DNN(Model):
    """Deep neuronal network predictive model.

    It is a full torch implementation. Complexity :math:`O(n)`.

    Attributes
    ----------
    niter : int
        The total number of iteration during the .fit method (read and write).
    learning_rate : float
        The adam learning rate durring the .fit method (read and write).

    """

    def __init__(
        self, niter: int=10000, learning_rate: float=1e-4, total: int | None=None, **kwargs: dict,
    ) -> None:
        r"""Define the gradient decrease convergence parameters.

        Parameters
        ----------
        \*\*kwargs
            Transmitted to :py:class:`mendevi.models.base.Model`.
        niter : int, default=1000
            The number of epoch, also the number of batch, because one batch by epoch.
        learning_rate : float, default=1e-4
            The learning rate.
        total : int, optional
            The number of parameters of the neuronal network.
            By default, the size if choosen according a simple heuristic
            based on the size of the training set.

        """
        if total is not None:
            assert isinstance(total, int), total.__class__.__name__
            assert total > 0, total
        self._total = total
        super().__init__(**kwargs)  # before niter and learning_rate to avoid reset
        assert isinstance(niter, int), niter.__class__.__name__
        assert niter >= 0, niter
        assert isinstance(learning_rate, float), learning_rate.__class__.__name__
        assert learning_rate > 0, learning_rate
        self._niter, self._lr = None, None
        self.niter = niter  # check and set through setter
        self.learning_rate = learning_rate  # check and set through setter

    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> object:
        """Perform the gradient descent on a just intanciated nn."""
        # intitialisation
        input_values = torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1)
        reference = torch.cat([values[lbl] for lbl in self.output_labels], dim=1)

        # handle nan values
        nanmask = ~input_values.isnan().any(dim=1)  # to discard corrupted input
        input_values, nanref = input_values[nanmask, :], reference[nanmask, :]
        nanmask = nanref.isnan()  # for output

        # end of initialization
        total = self._total or input_values.shape[0] // 4  # empirical rule
        model = _TorchNN(input_values.shape[1], nanref.shape[1], total=total)
        if self._weights is not None:
            model.load(
                (
                    f"{self._weights.stem.split(".")[0]}"
                    f"_{input_values.shape[1]}_{nanref.shape[1]}_{total}"
                ),
            )

        # train
        model.train()
        optimizer = torch.optim.Adam(model.parameters(), lr=self._lr)
        with tqdm.tqdm(
            desc="Gradient decay",
            dynamic_ncols=True,
            leave=False,
            smoothing=1e-6,
            total=self._niter,
        ) as progress_bar:
            for _ in range(self._niter):
                # prediction, ignore nan values in output
                predict = model(input_values)
                nanref[nanmask] = predict[nanmask].detach()  # ignore these values in gradient
                # gradient stuff
                loss = ((predict - nanref)**2).mean()
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                # display progression
                progress_bar.update(1)
                progress_bar.set_postfix_str(f"loss: {loss:9.3e}")
        model.eval()
        if self._weights is not None:
            model.save()

        # serialisation
        index = 0
        slices = {}
        for lbl in self.output_labels:
            slices[lbl] = (index, index+values[lbl].shape[1])
            index = slices[lbl][1]
        return (model, slices)

    def _predict_vect_norm(
        self, values: dict[str, torch.Tensor], parameters: object,
    ) -> dict[str, torch.Tensor]:
        """Inference part of the model."""
        # preparation, vectorisation
        input_values = torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1)
        model, slices = parameters

        # inference
        prediction = model(input_values)

        # parse result
        return {lbl: prediction[:, idx_min:idx_max] for lbl, (idx_min, idx_max) in slices.items()}

    @property
    def niter(self) -> int:
        """Ghe total number of iteration during the .fit method."""
        return self._niter

    @niter.setter
    def niter(self, niter: int) -> None:
        """Set total number of iteration during the .fit method."""
        assert isinstance(niter, int), niter.__class__.__name__
        assert niter >= 0, niter
        self._niter = niter

    @property
    def learning_rate(self) -> float:
        """Ghe the adam learning rate durring the .fit method."""
        return self._lr

    @learning_rate.setter
    def learning_rate(self, learning_rate: float) -> None:
        """Set the adam learning rate durring the .fit method."""
        assert isinstance(learning_rate, float), learning_rate.__class__.__name__
        assert learning_rate > 0.0, learning_rate
        self._lr = learning_rate


class EnergyNN(DNN):
    """Deep neuronal network for the video encoding energy prediction.

    Examples
    --------
    >>> from mendevi.models.nn import EnergyNN
    >>> model = EnergyNN(niter=100)
    >>> model = model.fit(
    ...     "scatter.db", table="t_enc_encode", select="uniform(vid_hash) >= 0.2",
    ... )
    >>> model.validate(
    ...     "scatter.db", table="t_enc_encode", select="uniform(vid_hash) < 0.2",
    ... )  # doctest: +SKIP
    >>>

    """

    def __init__(
        self,
        title: str = "Encoding energy estimation based on a neuronal network",
        **kwargs: dict,
    ) -> None:
        """Initialise the model."""
        kwargs = kwargs.copy()
        kwargs["input_labels"] = kwargs.get(
            "input_labels", [
                "encoder", "effort", "mode", "quality",
                "hostname",  # "temperature",
                "nb_frames", "height", "width",  # "range", "primaries", "eotf",
                "spatial_dct", "temporal_dct", "rms_sobel", "rms_time_diff",
            ],
        )
        kwargs["output_labels"] = kwargs.get(
            "output_labels",
            ["log_act_duration_per_frame", "power"],
        )
        kwargs["aggregation"] = kwargs.get("aggregation", ["hostname"])
        super().__init__(title=title, **kwargs)


class QualityNN(DNN):
    """Deep neuronal network for the video quality prediction.

    Examples
    --------
    >>> from mendevi.models.nn import QualityNN
    >>> model = QualityNN(output_labels=["psnr"], niter=100)
    >>> model = model.fit(
    ...     "scatter.db", table="t_enc_encode", select="uniform(vid_hash) >= 0.2",
    ... )
    >>> model.validate(
    ...     "scatter.db", table="t_enc_encode", select="uniform(vid_hash) < 0.2",
    ... )  # doctest: +SKIP
    >>>

    """

    def __init__(
        self,
        title: str = "Quality estimation based on a neuronal network",
        **kwargs: dict,
    ) -> None:
        """Initialise the model."""
        kwargs = kwargs.copy()
        kwargs["input_labels"] = kwargs.get(
            "input_labels", [
                "encoder", "effort", "mode", "quality",
                "nb_frames", "height", "width",  # "range", "primaries", "eotf",
                "spatial_dct", "temporal_dct", "rms_sobel", "rms_time_diff",
            ],
        )
        kwargs["output_labels"] = kwargs.get(
            "output_labels",
            ["lpips", "psnr", "ssim", "vif", "vmaf", "log_size_per_frame"],
        )
        kwargs["aggregation"] = kwargs.get("aggregation", [])
        super().__init__(title=title, **kwargs)
