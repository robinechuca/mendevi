# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Study the influence of one input parameter (independently of the other) on the output."""

import typing

import torch
import tqdm
from context_verbose import Printer

from .base import EPS, discard_nan
from .nn import DNN, _TorchNN
from mendevi.cst.labels import LABELS


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
        )  # hack to set self.input_labels_aggreg = self._interest_labels
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
                    total=160,
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
                y_est = {  # Ŷ
                    clus: {  # a*Y' + b
                        lbl: a_b[clus][lbl][:, 0:1].abs()*y_prime_[:, idx_min:idx_max] + a_b[clus][lbl][:, 1:2]
                        for lbl, (idx_min, idx_max) in slices.items()
                    }
                    for clus, y_prime_ in y_prime.items()
                }
                # losses and regularization
                losses = {  # loss for each output var and each cluster
                    clus: {
                        lbl: ((y_est__ - parameters[clus][lbl])**2).mean()
                        for lbl, y_est__ in y_est_.items()
                    }
                    for clus, y_est_ in y_est.items()
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
                    0.5*losses.pop("prod(a)") + 0.5*losses.pop("sum(b)")  # regularization
                    + torch.cat([ls[None] for ls in losses.values()]).mean()  # main loss
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
