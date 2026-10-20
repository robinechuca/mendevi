# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Study the influence of one input parameter (independently of the other) on the output."""

import typing

import torch
import tqdm
from context_verbose import Printer

from mendevi.cst.labels import LABELS

from .base import EPS, discard_nan
from .nn import DNN, _TorchNN


class TrendNormlisator(DNN):
    r"""Examines the relative impact of a set of parameters on an output.

    This structure provides an answer to the question:

    How does parameter :math:`X_k` affect parameter :math:`Y`,
    regardless of all other factors :math:`\left\{ X_i \right\}_{i \neq k}`?

    This model is an implementation of the diagram below.
    The parameters of the functions :math:`\phi'` and :math:`psi` are trained simultaneously.

    .. image:: /_static/media/intrinsic.svg
        :alt: Pipeline diagram

    Attributes
    ----------
    interest_labels : list[str]
        The name of all :math:`X_k` labels (readonly).
    context_labels : list[str]
        The name of all other labels :math:`\left\{ X_i \right\}_{i \neq k}` (readonly).

    """

    def __init__(self, interest_labels: list[str], **kwargs: dict) -> None:
        r"""Initialise the model.

        Parameters
        ----------
        interest_labels : list[str]
            The parameters whose impact we wish to study, it corresponds to :math:`X_k`.
            The possibles values are `mendevi.plot.axis.Name`.
        output_labels : list[str]
            The parameters affected, it corresponds to :math:`Y`.
            It is transmitted to the class :py:class:`mendevi.models.base.Model`.
        input_labels : list[str]
            All the other contextual input parameters that feed into :math:`\psi`.
            These correspond to the :math:`\left\{ X_i \right\}_{i \neq k}` set in the diagram.
            The ``input_labels`` transmitted to :py:class:`mendevi.models.base.Model` are
            the union of this ``input_labels`` and this ``interest_labels``.
        \*\*kwargs
            Transmitted to :py:class:`mendevi.models.nn.DNN`.

        Notes
        -----
        The parameter ``aggregation`` has only an impact on the function :math:`\psi`.
        :math:`\phi` is always the same / shared in all scenarios.

        """
        # check interest_labels
        assert hasattr(interest_labels, "__iter__"), interest_labels.__class__.__name__
        interest_labels = list(interest_labels)
        assert interest_labels, "interest must be not empty"
        assert all(isinstance(lab, str) and lab in LABELS for lab in interest_labels), \
            (interest_labels, sorted(LABELS))
        self._interest_labels = interest_labels

        # union for all input_labels
        single: set[str] = set()  # remove redundency
        input_labels: list[str] = []  # keep order
        for lbl in (*kwargs.get("input_labels", []), *interest_labels):
            if lbl in single:  # better than 'lbl in input_labels' becaose O(1) vs O(n)
                continue
            single.add(lbl)
            input_labels.append(lbl)  # we do not do list(set(...)) to preserve order
        super().__init__(**{**kwargs, "input_labels": input_labels})

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

        # create and warm the phi_prime global model
        self._aggreg_ctx = "full"  # for global normalization
        niter, self._niter = self._niter, self._niter//10  # model warming settings
        aggreg, input_labels, self._aggreg, self._input_labels = (
            self._aggreg, self._input_labels, [], self._interest_labels,
        )  # indirect way to set self.input_labels_aggreg = self._interest_labels
        phi_prime, slices = super()._fit_vect(  # based on self.input_labels_aggreg
            merge_values, _check=False,
        )
        self._niter = niter
        self._aggreg, self._input_labels = aggreg, input_labels

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
                "x_k": torch.cat([values[lbl] for lbl in self.interest_labels], dim=1),
                "x_i_no_k": torch.cat([values[lbl] for lbl in self.context_labels], dim=1),
                **values,
            }
            for clus, values in parameters.items()
        }

        # initialise the Xi, i!=k -> a, b denomalized heads hyperparameters
        psi = {
            clus: {
                lbl: _TorchNN(
                    in_ndim=parameters[clus]["x_i_no_k"].shape[1],
                    out_ndim=2,  # dim 2 for a and b
                    total=self._total or max(
                        parameters[clus]["x_i_no_k"].shape[1] + 8 + 2,  # minimum structural
                        parameters[clus]["x_i_no_k"].shape[0] // 4,  # empirical rule
                    ),
                )
                for lbl in slices
            }
            for clus in clus_keys
        }

        # gradient decay
        optimizer = torch.optim.RAdam(
            [
                *phi_prime.parameters(),
                *(p for ms in psi.values() for m in ms.values() for p in m.parameters()),
            ],
            lr=self._lr,
        )
        with (
            Printer(
                (
                    f"Global fit on {len(parameters)} clusters "
                    f"for {sum(len(d['x_k']) for d in parameters.values())} observations..."
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
                # prediction, X_k = values["input"]
                y_prime = {clus: phi_prime(values["x_k"]) for clus, values in parameters.items()}
                a_b = {
                    clus: {lbl: psi_(values["x_i_no_k"]) for lbl, psi_ in psi[clus].items()}
                    for clus, values in parameters.items()
                }
                y_hat = {  # Ŷ
                    clus: {  # a*Y' + b
                        lbl: (
                            a_b[clus][lbl][:, 0:1].abs()*y_prime_[:, idx_min:idx_max]
                            + a_b[clus][lbl][:, 1:2]
                        )
                        for lbl, (idx_min, idx_max) in slices.items()
                    }
                    for clus, y_prime_ in y_prime.items()
                }
                # losses and regularization
                losses = {  # loss for each output var and each cluster
                    clus: {
                        lbl: ((y_hat__ - parameters[clus][lbl])**2).mean()
                        for lbl, y_hat__ in y_hat_.items()
                    }
                    for clus, y_hat_ in y_hat.items()
                }
                losses = {  # average loss throw each clusters
                    lbl: torch.cat([loss[lbl][None] for loss in losses.values()]).mean()
                    for lbl in slices
                }
                losses = {  # add regularization
                    **losses,
                    "prod(a)": (torch.cat([
                        a_b__[:, 0] for a_b_ in a_b.values() for a_b__ in a_b_.values()
                    ]).abs() + EPS).log().sum(),
                    "sum(b)": torch.cat([
                        a_b__[:, 1] for a_b_ in a_b.values() for a_b__ in a_b_.values()
                    ]).sum(),
                }
                progress_bar.set_postfix_str(
                    ", ".join(f"{lbl}: {losses[lbl]:9.3e}" for lbl in sorted(losses)),
                )
                # gradient propagation
                optimizer.zero_grad()
                (  # note hack, the .pop remove regularization terme from main loss
                    1e-3*losses.pop("prod(a)") + 1e-3*losses.pop("sum(b)")  # regularization
                    + torch.cat([ls[None] for ls in losses.values()]).mean()  # main loss
                ).backward()
                optimizer.step()
                progress_bar.update(1)
            # sum up
            for lbl in sorted(losses):
                prt.print(f"mse {lbl}: {losses[lbl]:9.3e}")
            prt.print_time()

        return {clus: (phi_prime, slices, psi_, parameters[clus]) for clus, psi_ in psi.items()}

    def _predict_vect(
        self, values: dict[str, torch.Tensor], parameters: object,
    ) -> dict[str, torch.Tensor]:
        """Perform the prediction on a specific cluster."""
        # model, slices, heads, _ = parameters
        phi_prime, slices, psi, _ = parameters

        # data normalization and concatenation
        x_k = torch.cat(
            [
                (values[lbl] - self._std_mean["full"][lbl][1])
                / (self._std_mean["full"][lbl][0] + EPS)
                for lbl in self.interest_labels
            ],
            dim=1,
        )
        x_i_no_k = torch.cat(
            [
                (values[lbl] - self._std_mean["full"][lbl][1])
                / (self._std_mean["full"][lbl][0] + EPS)
                for lbl in self.context_labels
            ],
            dim=1,
        )

        # evaluation of latent Y' (normalized)
        y_prime = phi_prime(x_k)
        y_prime = {
            lbl: y_prime[:, idx_min:idx_max] for lbl, (idx_min, idx_max) in slices.items()
        }
        # evaluation final (normalized)
        a_b = {lbl: psi_(x_i_no_k) for lbl, psi_ in psi.items()}
        y_hat = {  # a*Y' + b
            lbl: a_b[lbl][:, 0:1].abs()*y_prime_ + a_b[lbl][:, 1:2]
            for lbl, y_prime_ in y_prime.items()
        }

        # denormalization
        return {  # y_hat
            lbl: y_hat_ * (self._std_mean["full"][lbl][0] + EPS) + self._std_mean["full"][lbl][1]
            for lbl, y_hat_ in y_hat.items()
        }

    @property
    def context_labels(self) -> list[str]:
        r"""Return the name of all other labels :math:`\left\{ X_i \right\}_{i \neq k}`."""
        return sorted(set(self.input_labels_aggreg) - set(self._interest_labels))

    def fit(self, *args: tuple, **kwargs: dict) -> typing.Self:
        """Container for the :py:meth:`Model.fit` method."""
        super().fit(*args, **kwargs)  # prepare data
        self._parameters = self._delay_fit()  # create and train all models
        if self._weights is not None:  # save again
            self.save(self._weights)
        return self

    @property
    def interest_labels(self) -> list[str]:
        """Return the name of all :math:`X_k` labels."""
        return self._interest_labels.copy()

    def draw(self) -> None:
        """Plot the R -> R heads function."""
        if len(self.interest_labels) != 1:
            msg = f"to draw the impact, only one interest label has to be given, not {self.interest_labels}"
            raise ValueError(msg)
        (interest_label,) = self.interest_labels
        import matplotlib.pyplot as plt  # noqa: PLC0415
        from mendevi.cst.plot import COLORS, MARKERS
        clus_data_psi = {clus: (data, psi) for clus, (_, _, psi, data) in self._parameters.items()}
        phi_prime, slices, _, _ = next(iter(self._parameters.values()))
        for lbl, (idx_min, idx_max) in slices.items():
            plt.xlabel(f"{interest_label} ($X_k$)")
            plt.ylabel(f"{lbl} ($Y'$)")
            for i, (clus, (data, psi)) in enumerate(clus_data_psi.items()):
                # compute y_prime
                x_k = data[interest_label]
                y_prime = phi_prime(data[interest_label])[:, idx_min:idx_max]

                # plot phi_'
                x_k_denorm = x_k * (self._std_mean["full"][interest_label][0] + EPS) + self._std_mean["full"][interest_label][1]
                y_prime_denorm = y_prime * (self._std_mean["full"][lbl][0] + EPS) + self._std_mean["full"][lbl][1]
                plt.scatter(
                    x_k_denorm.ravel().tolist(),  # TODO traitement plus malin
                    y_prime_denorm.ravel().tolist(),
                    label=str(clus),
                    color=COLORS[i%len(COLORS)],
                    marker=MARKERS[0],
                )

                # compute y_hat
                x_i_no_k = data["x_i_no_k"]
                a_b = psi[lbl](x_i_no_k)
                y_hat = a_b[:, 0:1].abs()*y_prime + a_b[:, 1:2]

                # plot phi_hat
                y_hat_denorm = y_hat * (self._std_mean["full"][lbl][0] + EPS) + self._std_mean["full"][lbl][1]
                plt.scatter(
                    x_k_denorm.ravel().tolist(),  # TODO traitement plus malin
                    y_hat_denorm.ravel().tolist(),
                    # label=str(clus),
                    color=COLORS[i%len(COLORS)],
                    marker=MARKERS[1],
                    alpha=0.1,
                )

            plt.legend()
            plt.show()


class TrendEncodeEnergy(TrendNormlisator):
    """Examine the effect of a parameter on encoding time and power.

    This example provides an overview of the effect of quality on energy consumption:

    Examples
    --------
    >>> from mendevi.models.trend import TrendEncodeEnergy
    >>> model = TrendEncodeEnergy(interest_labels=["quality"]).fit(
    ...     "scatter.db", table="t_enc_encode", select="uniform(vid_hash) >= 0.2",
    ... )  # doctest: +SKIP
    >>> model.validate(
    ...     "scatter.db", table="t_enc_encode", select="uniform(vid_hash) < 0.2",
    ... )  # doctest: +SKIP
    >>>

    """

    def __init__(
        self,
        title: str = "Effect of a parameter on the encoding energy",
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


# class DecodeEnergyNN(TrendNormlisator):
#     """Deep neuronal network for the video encoding energy prediction.

#     Examples
#     --------
#     >>> from mendevi.models.trend import DecodeEnergyNN
#     >>> model = DecodeEnergyNN().fit(
#     ...     "duration.db", table="t_dec_decode", select="uniform(vid_hash) >= 0.2",
#     ... )  # doctest: +SKIP
#     >>> model.validate(
#     ...     "duration.db", table="t_dec_decode", select="uniform(vid_hash) < 0.2",
#     ... )  # doctest: +SKIP
#     >>>

#     """

#     def __init__(
#         self,
#         title: str = "Decoding energy estimation based on a neuronal network",
#         **kwargs: dict,
#     ) -> None:
#         """Initialise the model."""
#         kwargs = kwargs.copy()
#         kwargs["input_labels"] = kwargs.get(
#             "input_labels", [
#                 "decoder",
#                 "hostname",  # "temperature",
#                 "nb_frames", "height", "width",  # "range", "primaries", "eotf",
#                 "spatial_dct", "temporal_dct", "rms_sobel", "rms_time_diff",
#             ],
#         )
#         kwargs["output_labels"] = kwargs.get(
#             "output_labels", ["log_act_duration_per_frame", "power"],
#         )
#         kwargs["aggregation"] = kwargs.get("aggregation", ["hostname"])
#         super().__init__(title=title, **kwargs)
