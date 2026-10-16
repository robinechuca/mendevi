# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Study the influence of one input parameter (independently of the other) on the output."""

import typing

import torch
import tqdm
from context_verbose import Printer

from .base import EPS, discard_nan
from .nn import DNN, _TorchNN


class KernelMultiHead(DNN):
    """Share the kernel NN to all aggregated data, and split output with several headers.

    This structure provides an answer to the question:

    **How does parameter ``toto`` affect parameter ``tata``, regardless of all other factors?**

    {xi}                  +-----+
        i>=1              |     |                            y
    --------------------->| phi |--------------------------------->
                          |     |
                          +-----+

    

    .. image:: /_static/media/intrinsic.svg
        :alt: Pipeline diagram
    """

    def _fit_vect(self, values: dict[str, torch.Tensor]) -> object:
        """Hack to delay the model instantation and training."""
        return values  # no normalization to avoid a subnormalisation by cluster

    def _delay_fit(self) -> dict[str, tuple]:
        """Create a unique model to fit all the clusters at the same time.

        It has to be called after the classical ``.fit()`` method.
        """
        # merge cluster data
        clus_keys = list(self._parameters)  # to frozen order
        merge_values = {  # concatenate the data of all clusters
            lbl: torch.cat(
                [self._parameters[clus_key][lbl] for clus_key in clus_keys], dim=0,
            )
            for lbl in (*self.input_labels_aggreg, *self.output_labels)
        }

        # create and warm the kernel common nn model
        self._aggreg_ctx = "full"  # for global normalization
        niter, self._niter = self._niter, self._niter//10  # universal model warming
        model, slices = super()._fit_vect(merge_values)
        self._niter = niter

        # parameters preparation
        parameters = {  # normalisation
            clus: {
                lbl: (
                    (data - self._std_mean["full"][lbl][1]) / (self._std_mean["full"][lbl][0] + EPS)
                )
                for lbl, data in values.items()
            }
            for clus, values in self._parameters.items()
        }
        parameters = {  # filtering
            clus: discard_nan(values) for clus, values in parameters.items()
        }
        parameters = {  # concatenation
            clus: {
                "input": torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1),
                **values,
            }
            for clus, values in parameters.items()
        }

        # initialise the R -> R heads, they are simple enouth to approximate a smouth ID
        heads = {
            clus: {
                lbl: _TorchNN(in_ndim=idx_max-idx_min, out_ndim=idx_max-idx_min, total=80)
                for lbl, (idx_min, idx_max) in slices.items()
            }
            for clus in clus_keys
        }

        # gradient decay
        optimizer = torch.optim.RAdam(
            [
                *model.parameters(),
                *(p for ms in heads.values() for m in ms.values() for p in m.parameters()),
            ],
            lr=self._lr,
        )
        with (
            Printer(
                (
                    f"Global fit on {len(parameters)} clusters "
                    f"for {sum(len(d['input']) for d in parameters.values())} observations..."
                ),
                color="pink",
            ) as prt,
            tqdm.tqdm(
                desc="Gradient decay",
                dynamic_ncols=True,
                leave=False,
                smoothing=1e-6,
                total=self._niter,
            ) as progress_bar,
        ):
            for _ in range(self._niter):
                # prediction
                intrinsic = {clus: model(values["input"]) for clus, values in parameters.items()}
                predict = {
                    clus: {
                        lbl: data[:, idx_min:idx_max] + heads[clus][lbl](data[:, idx_min:idx_max])
                        for lbl, (idx_min, idx_max) in slices.items()
                    }
                    for clus, data in intrinsic.items()
                }
                # losses and regularization
                losses = {  # main mse loss
                    clus: {
                        lbl: ((data_pred[lbl] - parameters[clus][lbl])**2).mean()
                        for lbl, (idx_min, idx_max) in slices.items()
                    }
                    for clus, data_pred in predict.items()
                }
                losses = {  # average loss throw each clusters
                    lbl: torch.cat([loss[lbl][None] for loss in losses.values()]).mean()
                    for lbl in slices
                }
                progress_bar.set_postfix_str(
                    ", ".join(f"{lbl}: {losses[lbl]:9.3e}" for lbl in sorted(losses)),
                )
                identity_regularization = torch.cat([  # regularisation term to force identity
                    ((data[:, idx_min:idx_max] - predict[clus][lbl])**2).mean()[None]
                    for clus, data in intrinsic.items()
                    for lbl, (idx_min, idx_max) in slices.items()
                ]).mean()
                # gradient propagation
                optimizer.zero_grad()
                (
                    torch.cat([ls[None] for ls in losses.values()]).mean()  # main loss
                    + 0.5 * identity_regularization  # force latent space to be homogeneous
                ).backward()
                optimizer.step()
                progress_bar.update(1)
            # sum up
            for lbl in sorted(losses):
                prt.print(f"mse {lbl}: {losses[lbl]:9.3e}")
            prt.print_time()

        return {clus: (model, slices, head, parameters[clus]) for clus, head in heads.items()}

    def _predict_vect(
        self, values: dict[str, torch.Tensor], parameters: object,
    ) -> dict[str, torch.Tensor]:
        """Perform the prediction on a specific cluster."""
        model, slices, heads, _ = parameters

        # data normalization and concatenation
        normalized_data = torch.cat(
            [
                (values[lbl] - self._std_mean["full"][lbl][1])
                / (self._std_mean["full"][lbl][0] + EPS)
                for lbl in self.input_labels_aggreg
            ],
            dim=1,
        )

        # evaluation latent intrinsic (normalized)
        prediction = model(normalized_data)
        prediction = {
            lbl: prediction[:, idx_min:idx_max] for lbl, (idx_min, idx_max) in slices.items()
        }
        # evaluation final (normalized)
        prediction = {lbl: pred + heads[lbl](pred) for lbl, pred in prediction.items()}  # optional

        # denormalization
        prediction = {
            lbl: pred * (self._std_mean["full"][lbl][0] + EPS) + self._std_mean["full"][lbl][1]
            for lbl, pred in prediction.items()
        }

        return prediction

    def fit(self, *args: tuple, **kwargs: dict) -> typing.Self:
        """Container for the :py:meth:`Model.fit` method."""
        super().fit(*args, **kwargs)  # prepare data
        self._parameters = self._delay_fit()  # create and train all models
        if self._weights is not None:  # save again
            self.save(self._weights)
        return self

    def draw(self) -> None:
        """Plot the R -> R heads function."""
        import matplotlib.pyplot as plt  # noqa: PLC0415
        heads_data = {clus: (head, data) for clus, (_, _, head, data) in self._parameters.items()}
        model, slices, _, _ = next(iter(self._parameters.values()))
        for lbl, (idx_min, idx_max) in slices.items():
            plt.xlabel(f"{lbl} intrinsec")
            plt.ylabel(f"{lbl} absolute")
            for clus, (head, data) in heads_data.items():
                trad_model = head[lbl]
                # mini, maxi = model(data["input"])[:, idx_min:idx_max].aminmax()
                # plt.plot(
                #     (
                #         torch.linspace(mini, maxi, 1000) * self._std_mean["full"][lbl][0]
                #         + self._std_mean["full"][lbl][1]
                #     ).numpy(force=True).ravel(),
                #     (
                #         (
                #             torch.linspace(mini, maxi, 1000)[:, None]
                #             + trad_model(torch.linspace(mini, maxi, 1000)[:, None])
                #         )
                #         * self._std_mean["full"][lbl][0] + self._std_mean["full"][lbl][1]
                #     ).numpy(force=True).ravel(),
                #     label=str(clus),
                # )

                lattent = model(data["input"])[:, idx_min:idx_max]
                plt.scatter(
                    (
                        lattent * self._std_mean["full"][lbl][0]
                        + self._std_mean["full"][lbl][1]
                    ).numpy(force=True).ravel(),
                    (
                        (lattent + trad_model(lattent))
                        * self._std_mean["full"][lbl][0] + self._std_mean["full"][lbl][1]
                    ).numpy(force=True).ravel(),
                    label=str(clus),
                )

            plt.legend()
            plt.show()


class EncodeEnergyNN(KernelMultiHead):
    """Deep neuronal network for the video encoding energy prediction.

    Examples
    --------
    >>> from mendevi.models.trend import EncodeEnergyNN
    >>> model = EncodeEnergyNN().fit(
    ...     "svtav1_vs_rav1e_vs_aom.db", table="t_enc_encode", select="uniform(vid_hash) >= 0.2",
    ... )  # doctest: +SKIP
    >>> model.validate(
    ...     "svtav1_vs_rav1e_vs_aom.db", table="t_enc_encode", select="uniform(vid_hash) >= 0.2",
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


class DecodeEnergyNN(KernelMultiHead):
    """Deep neuronal network for the video encoding energy prediction.

    Examples
    --------
    >>> from mendevi.models.trend import DecodeEnergyNN
    >>> model = DecodeEnergyNN().fit(
    ...     "duration.db", table="t_dec_decode", select="uniform(vid_hash) >= 0.2",
    ... )  # doctest: +SKIP
    >>> model.validate(
    ...     "duration.db", table="t_dec_decode", select="uniform(vid_hash) < 0.2",
    ... )  # doctest: +SKIP
    >>>

    """

    def __init__(
        self,
        title: str = "Decoding energy estimation based on a neuronal network",
        **kwargs: dict,
    ) -> None:
        """Initialise the model."""
        kwargs = kwargs.copy()
        kwargs["input_labels"] = kwargs.get(
            "input_labels", [
                "decoder",
                "hostname",  # "temperature",
                "nb_frames", "height", "width",  # "range", "primaries", "eotf",
                "spatial_dct", "temporal_dct", "rms_sobel", "rms_time_diff",
            ],
        )
        kwargs["output_labels"] = kwargs.get(
            "output_labels", ["log_act_duration_per_frame", "power"],
        )
        kwargs["aggregation"] = kwargs.get("aggregation", ["hostname"])
        super().__init__(title=title, **kwargs)
