# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Predict the energy and the quality based on a neuronal network."""

import torch
import tqdm

from .base import Model


class _TorchNN(torch.nn.Module):
    """Simple perceptron nn."""

    def __init__(self, in_ndim: int, out_ndim: int, total: int) -> None:
        # verifications
        assert isinstance(in_ndim, int), in_ndim.__class__.__name__
        assert in_ndim >= 1, in_ndim
        assert isinstance(out_ndim, int), out_ndim.__class__.__name__
        assert out_ndim >= 1, out_ndim
        assert isinstance(total, int), total.__class__.__name__
        assert total >= in_ndim + 8 + out_ndim, total
        super().__init__()
        torch.manual_seed(0)  # for reproductibility
        # solve total = in_ndim*fact + fact * 2*fact + 2*fact * fact + fact*out_ndim
        delta = (in_ndim + out_ndim)**2 + 16*total
        fact = (delta**.5 - in_ndim - out_ndim) / 8
        fact = round(fact)
        # 4 full connected layers (better without dropout)
        self.linear = torch.nn.Sequential(
            torch.nn.Linear(in_ndim, fact),
            torch.nn.ELU(),

            torch.nn.Linear(fact, 2*fact),
            torch.nn.BatchNorm1d(2*fact),  # just this batch norm, no more
            torch.nn.ELU(),

            torch.nn.Linear(2*fact, fact),
            torch.nn.ELU(),

            torch.nn.Linear(fact, out_ndim),
        )

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


class DNN(Model):
    """Deep neuronal network predictive model."""

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
        self._niter, self._lr = niter, learning_rate

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
        total = self._total or max(
            input_values.shape[1] + 8 + nanref.shape[1],  # minimum structural
            input_values.shape[0] // 4,  # empirical rule
        )
        model = _TorchNN(input_values.shape[1], nanref.shape[1], total=total)

        # train
        model.train()
        optimizer = torch.optim.RAdam(model.parameters(), lr=self._lr)
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


class QualityNN(DNN):
    """Deep neuronal network for the video quality prediction.

    Examples
    --------
    >>> from mendevi.models.nn import QualityNN
    >>> model = QualityNN(output_labels=["psnr"])
    >>> _ = model.fit(
    ...     "svtav1_vs_rav1e_vs_aom.db", table="t_enc_encode", select="uniform(vid_hash) >= 0.2",
    ... )  # doctest: +SKIP
    >>> model.validate(
    ...     "svtav1_vs_rav1e_vs_aom.db", table="t_enc_encode", select="uniform(vid_hash) < 0.2",
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
