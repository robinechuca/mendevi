# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Study the influence of one input parameter (independently of the other) on the output."""

import hashlib
import math
import typing

import torch
import tqdm
from context_verbose import Printer
from matplotlib import axes, figure, ticker

from mendevi.cst.labels import LABELS
from mendevi.cst.plot import COLORS, MARKERS, MARKERSIZE
from mendevi.database.meta import get_extractor

from .base import EPS, discard_nan, from_torch
from .nn import DNN, _TorchNN

LINPLOT: int = 1000  # the number of points used for continuous plot curves
REGULARIZATION_FACTOR: float = 1e-2  # regularisation terms a and b in relation to the model error


class Psi(_TorchNN):
    """For a context variable, determine the correction pair a and b.

    Examples
    --------
    >>> import torch
    >>> from mendevi.models.trend import Psi
    >>> psi = Psi("cores", 1, 330)
    >>> psi
    Psi('cores', 1, 330)
    >>>
    >>> _ = torch.manual_seed(0)
    >>> psi(torch.randn(10, 1))
    tensor([[ 1.1574, -0.2972],
            [ 1.1662, -0.2130],
            [ 1.1872, -0.3771],
            [ 1.1881, -0.2382],
            [ 1.1581, -0.2677],
            [ 1.1631, -0.2955],
            [ 1.1905, -0.2266],
            [ 1.1818, -0.2561],
            [ 1.1569, -0.2398],
            [ 1.1612, -0.2203]], grad_fn=<CatBackward0>)
    >>>

    """

    def __init__(self, label: str, ndim: int, total: int) -> None:
        """Initialise the simple perceptron model.

        Parameters
        ----------
        label: str
            The name of the parameter. The possibles values are `mendevi.plot.axis.Name`.
        ndim : int
            The dimension of the input label, often 1, except for one hot encoding.
        total : int
            The total weight of the model.

        """
        assert isinstance(label, str), label.__class__.__name__
        assert label in LABELS, (label, sorted(LABELS))
        self._label = label
        super().__init__(ndim, 2, total)
        self._std_mean: tuple[float, float] | None = None
        self._values: torch.Tensor | None = None

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        """Exponential normalization of a and b."""
        a_b = super().forward(values)
        return torch.cat([torch.exp(a_b[:, 0, None]), torch.sinh(a_b[:, 1, None])], dim=1)

    def fill_axe(
        self,
        axe: axes.Axes,
        values: torch.Tensor,
        std_mean: tuple[float, float] | None,
    ) -> None:
        """Fill the axis with the provided data.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> import torch
        >>> from mendevi.cst.plot import FIGSIZE
        >>> from mendevi.models.trend import Psi
        >>>
        >>> psi = Psi("cores", 1, 330)
        >>> _ = torch.manual_seed(0)
        >>> cores = torch.rand(10, 1) * 16
        >>> std_mean = (torch.std(cores, dim=0), torch.mean(cores, dim=0))
        >>> cores = (cores - std_mean[1]) / std_mean[0]
        >>>
        >>> fig = plt.figure(layout="constrained", figsize=FIGSIZE)
        >>> axe = fig.subplots(nrows=1, ncols=1, squeeze=True)
        >>> psi.fill_axe(axe, cores, std_mean)
        >>> _ = plt.legend()
        >>> plt.show()  # doctest: +SKIP
        >>>

        """
        # computes values
        a_b = self.forward(values)
        a_matplotlib, b_matplotlib = a_b[:, 0].tolist(), a_b[:, 1].tolist()
        values_matplotlib = from_torch(  # denormalize and convert into list
            {self._label: values * (std_mean[0]+EPS) + std_mean[1]},
        ).pop(self._label)

        # fill plot
        axe.scatter(
            values_matplotlib,
            a_matplotlib,
            color=COLORS[0],
            marker=MARKERS[0],
            s=MARKERSIZE**2,
            label="a",
        )
        axe.scatter(
            values_matplotlib,
            b_matplotlib,
            color=COLORS[1],
            marker=MARKERS[0],
            s=MARKERSIZE**2,
            label="b",
        )

        # metadata
        axe.set_title(self._label)
        axe.set_xscale("linear")
        axe.grid(axis="x", which="major")
        axe.grid(axis="x", which="minor", color="0.9")
        ticks = axe.xaxis.get_majorticklocs()  # get main graduations
        axe.xaxis.set_minor_locator(ticker.MultipleLocator((ticks[1] - ticks[0]) / 10.0))
        axe.set_yscale("linear")
        axe.grid(axis="y", which="major")
        axe.grid(axis="y", which="minor", color="0.9")
        ticks = axe.yaxis.get_majorticklocs()
        axe.yaxis.set_minor_locator(ticker.MultipleLocator((ticks[1] - ticks[0]) / 10.0))

        # plt.supylabel("Absolute context values")
        # plt.supxlabel("Denormalizator values a and b")

    @property
    def std_mean(self) -> tuple[float | torch.Tensor, float | torch.Tensor]:
        """Return the std and the mean for the input value denormalization."""
        if self._std_mean is None:
            raise AttributeError
        return self._std_mean

    @std_mean.setter
    def std_mean(self, std_mean: tuple[float | torch.Tensor, float | torch.Tensor]) -> None:
        """Set the std and the mean for the input value denormalization."""
        assert isinstance(std_mean, tuple), std_mean.__class__.__name__
        assert len(std_mean) == 2, std_mean
        assert isinstance(std_mean[0], float | torch.Tensor), std_mean[0].__class__.__name__
        assert isinstance(std_mean[1], float | torch.Tensor), std_mean[1].__class__.__name__
        self._std_mean = std_mean

    @property
    def values(self) -> torch.Tensor:
        """The example values, of shape (n, d)."""
        if self._values is None:
            raise AttributeError
        return self._data

    @values.setter
    def values(self, values: torch.Tensor) -> None:
        """Store the example data."""
        assert isinstance(values, torch.Tensor), values.__class__.__name__
        assert values.ndim == 2, values.shape
        self._values = values.detach().clone()

    def __repr__(self) -> str:
        """Simplify the representation."""
        ndim = self.linear[0].in_features
        total = sum(p.numel() for p in self.parameters())
        return f"{self.__class__.__name__}({self._label!r}, {ndim}, {total})"


class TrendNormlisator(DNN):
    r"""Examines the relative impact of a set of parameters on an output.

    This structure provides an answer to the question:

    How does parameter :math:`X_k` affect parameter :math:`Y`,
    regardless of all other factors :math:`\left\{ X_i \right\}_{i \neq k}`?

    This model is an implementation of the diagram below.
    The parameters of the functions :math:`\phi'` and :math:`psi` are trained simultaneously.

    .. image:: /_static/media/trend.svg
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

        # create and warm the phi_tilde global model
        self._aggreg_ctx = "full"  # for global normalization
        niter, self._niter = self._niter, 1  # model warming settings
        aggreg, input_labels, self._aggreg, self._input_labels = (
            self._aggreg, self._input_labels, [], self._interest_labels,
        )  # indirect way to set self.input_labels_aggreg = self._interest_labels
        phi_tilde, slices = super()._fit_vect(  # based on self.input_labels_aggreg
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
                "x_k": torch.cat([values[out_lbl] for out_lbl in self.interest_labels], dim=1),
                **values,
            }
            for clus, values in parameters.items()
        }

        # initialise the Xi, i!=k -> a, b denomalized heads hyperparameters
        psi = {
            clus: {
                in_lbl: Psi(
                    label=in_lbl,
                    ndim=parameters[clus][in_lbl].shape[1],
                    total=self._total or parameters[clus][in_lbl].shape[0] // 4,  # empirical rule
                )
                for in_lbl in self.context_labels
            }
            for clus in clus_keys
        }
        if self._weights is not None:  # if they exist, retrieve trained weights
            for clus in clus_keys:
                for lbl in self.context_labels:
                    psi[clus][lbl].load(
                        (
                            f"{self._weights.stem.split(".")[0]}"
                            f"_{lbl}_{hashlib.md5(str(clus).encode()).hexdigest()}"
                        ),
                    )

        # gradient decay
        optimizer = torch.optim.Adam(
            [
                *phi_tilde.parameters(),
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
                y_tilde = {clus: phi_tilde(values["x_k"]) for clus, values in parameters.items()}
                a_b = {  # all a and b
                    clus: torch.cat(
                        [psi_(values[lbl])[:, :, None] for lbl, psi_ in psi[clus].items()], dim=2,
                    )
                    for clus, values in parameters.items()
                }
                a_b = {  # reduce a and b, to 1d vector
                    clus: (
                        a_b_[:, 0, :].log().mean(dim=1, keepdim=True).exp(),  # geometric mean
                        a_b_[:, 1, :].mean(dim=1, keepdim=True),  # arithmetic mean
                    )
                    for clus, a_b_ in a_b.items()
                }
                y_hat = {  # Ŷ
                    clus: {  # a*Y + b
                        out_lbl: (
                            a_b[clus][0]*y_tilde_[:, idx_min:idx_max] + a_b[clus][1]
                        )
                        for out_lbl, (idx_min, idx_max) in slices.items()
                    }
                    for clus, y_tilde_ in y_tilde.items()
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
                    "a": torch.cat([  # loss geometric_mean(a) = 1
                        a_b_[0] for a_b_ in a_b.values()
                    ]).log().mean()**2,
                    "b": torch.cat([  # loss arithmetic_mean(b) = 0
                        a_b_[1] for a_b_ in a_b.values()
                    ]).mean()**2,
                }
                progress_bar.set_postfix_str(
                    ", ".join(f"{lbl}: {losses[lbl]:9.3e}" for lbl in sorted(losses)),
                )
                # gradient propagation
                optimizer.zero_grad()
                (  # note hack, the .pop remove regularization terme from main loss
                    REGULARIZATION_FACTOR*losses.pop("a")  # regularization
                    + REGULARIZATION_FACTOR*losses.pop("b")  # regularization
                    + torch.cat([ls[None] for ls in losses.values()]).mean()  # main loss
                ).backward()
                optimizer.step()
                progress_bar.update(1)
            # sum up
            for lbl in sorted(losses):
                prt.print(f"mse {lbl}: {losses[lbl]:9.3e}")
            prt.print_time()

        # save
        if self._weights is not None:
            phi_tilde.save()
            for clus in clus_keys:
                for lbl in self.context_labels:
                    psi[clus][lbl].save()

        return {clus: (phi_tilde, slices, psi_, parameters[clus]) for clus, psi_ in psi.items()}

    def _predict_vect(
        self, values: dict[str, torch.Tensor], parameters: object,
    ) -> dict[str, torch.Tensor]:
        """Perform the prediction on a specific cluster."""
        phi_tilde, slices, psi, _ = parameters

        # data normalization and concatenation
        x_k = torch.cat(
            [
                (values[out_lbl] - self._std_mean["full"][out_lbl][1])
                / (self._std_mean["full"][out_lbl][0] + EPS)
                for out_lbl in self.interest_labels
            ],
            dim=1,
        )
        x_i_no_k = {
            in_lbl: (
                (values[in_lbl] - self._std_mean["full"][in_lbl][1])
                / (self._std_mean["full"][in_lbl][0] + EPS)
            )
            for in_lbl in self.context_labels
        }

        # evaluation of latent Y_tilde (normalized)
        y_tilde = phi_tilde(x_k)
        y_tilde = {
            out_lbl: y_tilde[:, idx_min:idx_max] for out_lbl, (idx_min, idx_max) in slices.items()
        }
        # evaluation final (normalized)
        a_b = torch.cat([psi_(x_i_no_k[in_lbl])[:, :, None] for in_lbl, psi_ in psi.items()], dim=2)
        a_b = (
            a_b[:, 0, :].log().mean(dim=1, keepdim=True).exp(),  # geometric mean
            a_b[:, 1, :].mean(dim=1, keepdim=True),  # arithmetic mean
        )
        y_hat = {  # a*Y_tilde + b
            out_lbl: a_b[0]*y_tilde_ + a_b[1] for out_lbl, y_tilde_ in y_tilde.items()
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

    def fill_fig_phi(self, fig: figure.Figure | figure.SubFigure) -> None:
        """Complete the matplotlib figure with the :math:`\\tilde{\\phi}` subplots.

        .. note::
            The graph uses only training data, no validation.

        There is one color per cluster formed by the ``aggregation`` attribute.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from mendevi.cst.plot import FIGSIZE
        >>> from mendevi.models.trend import TrendNormlisator
        >>>
        >>> model = TrendNormlisator(
        ...     input_labels=["effort", "encoder", "pixels"], aggregation=[],
        ...     interest_labels=["quality"], output_labels=["log_bitrate"],
        ...     niter=100,  # very little to be fast
        ... ).fit("scatter.db", table="t_enc_encode", select="uniform(vid_hash) >= 0.2")
        >>> fig = plt.figure(layout="constrained", figsize=FIGSIZE)
        >>> model.fill_fig_phi(fig)
        >>> _ = plt.legend()
        >>> plt.show()  # doctest: +SKIP
        >>>

        """
        # verifications
        assert isinstance(fig, figure.Figure | figure.SubFigure), fig.__class__.__name__
        if len(self.interest_labels) != 1:
            msg = (
                "to draw the trend, only one interest label has to be given, "
                f"not {self.interest_labels}"
            )
            raise RuntimeError(msg)
        if not self._parameters:
            msg = "before drawing phi, you must train the model using the .fit(...) method"
            raise RuntimeError(msg)

        # precompute
        (interest_label,) = self.interest_labels
        clus_data_psi = {clus: (data, psi) for clus, (_, _, psi, data) in self._parameters.items()}
        phi_tilde, slices, _, _ = next(iter(self._parameters.values()))

        # matplotlib stuff
        nrows = int(math.sqrt(len(self.output_labels)))
        ncols = math.ceil(len(self.output_labels) / nrows)
        for lbl, axe in zip(
            self.output_labels,
            fig.subplots(
                nrows,
                ncols,
                squeeze=False,
                sharex="all",
                sharey=None,
            ).ravel(),
            strict=False,
        ):

            # compute cloud points
            for i, (clus, (data, psi)) in enumerate(clus_data_psi.items()):
                idx_min, idx_max = slices[lbl]

                # compute y_tilde (train data)
                x_k = data[interest_label]
                amin, amax = torch.aminmax(x_k, dim=0)
                x_k = torch.cat([  # adds LINPLOT continuous values at the start
                    (
                        torch.linspace(0, 1, LINPLOT, dtype=x_k.dtype, device=x_k.device)[:, None]
                        * (amax - amin)
                        + amin
                    ),
                    x_k,
                ], dim=0)
                x_k_denorm = (
                    x_k * (self._std_mean["full"][interest_label][0] + EPS)
                    + self._std_mean["full"][interest_label][1]
                )
                y_tilde = phi_tilde(x_k)[:, idx_min:idx_max]
                y_tilde_denorm = (
                    y_tilde * (self._std_mean["full"][lbl][0]+EPS) + self._std_mean["full"][lbl][1]
                )

                # plot y_tilde
                axe.plot(
                    x_k_denorm[:LINPLOT, 0].tolist(),
                    y_tilde_denorm[:LINPLOT, 0].tolist(),
                    "--",
                    color=COLORS[i%len(COLORS)],
                    zorder=3,
                )
                axe.scatter(
                    x_k_denorm[LINPLOT:, 0].tolist(),
                    y_tilde_denorm[LINPLOT:, 0].tolist(),
                    label=" and ".join(map(str, clus)) or None,
                    color=COLORS[i%len(COLORS)],
                    marker=MARKERS[0],
                )

                # compute y_hat
                a_b = torch.cat(
                    [psi_(data[in_lbl])[:, :, None] for in_lbl, psi_ in psi.items()], dim=2,
                )
                a_b = (
                    a_b[:, 0, :].log().mean(dim=1, keepdim=True).exp(),  # geometric mean
                    a_b[:, 1, :].mean(dim=1, keepdim=True),  # arithmetic mean
                )
                y_hat = a_b[0]*y_tilde[LINPLOT:, :] + a_b[1]
                y_hat_denorm = (
                    y_hat * (self._std_mean["full"][lbl][0]+EPS) + self._std_mean["full"][lbl][1]
                )

                # plot y_hat
                axe.scatter(
                    x_k_denorm[LINPLOT:, 0].tolist(),
                    y_hat_denorm[:, 0].tolist(),
                    color=COLORS[i%len(COLORS)],
                    marker=MARKERS[1],
                    alpha=0.1,
                )

                # plot y_reference
                axe.scatter(
                    x_k_denorm[LINPLOT:, 0].tolist(),
                    (
                        data[lbl] * (self._std_mean["full"][lbl][0]+EPS)
                        + self._std_mean["full"][lbl][1]
                    )[:, 0].tolist(),
                    color=COLORS[i%len(COLORS)],
                    marker=MARKERS[2],
                    alpha=0.1,
                )

            # axe.set_title(lbl)
            axe.scatter([], [], color="grey", marker=MARKERS[1], label="prediction $\\hat{Y}$")
            axe.scatter([], [], color="grey", marker=MARKERS[2], label="ground truth $Y$")
            axe.plot([], [], "--", color="grey", label="$\\tilde{\\phi}$")
            axe.set_ylabel(get_extractor(lbl, safe=True).legend)
            axe.set_xscale("linear")
            axe.grid(axis="x", which="major")
            axe.grid(axis="x", which="minor", color="0.9")
            ticks = axe.xaxis.get_majorticklocs()  # get main graduations
            axe.xaxis.set_minor_locator(ticker.MultipleLocator((ticks[1] - ticks[0]) / 10.0))
            axe.set_yscale("linear")
            axe.grid(axis="y", which="major")
            axe.grid(axis="y", which="minor", color="0.9")
            ticks = axe.yaxis.get_majorticklocs()
            axe.yaxis.set_minor_locator(ticker.MultipleLocator((ticks[1] - ticks[0]) / 10.0))

        fig.supxlabel(get_extractor(interest_label, safe=True).legend)

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

    @property
    def psi(self) -> dict[tuple, dict[str, Psi]]:
        """Returns all the psi functions.

        Returns a reference to psi without creating a copy.

        Examples
        --------
        >>> from pprint import pprint
        >>> from mendevi.models.trend import TrendNormlisator
        >>> model = TrendNormlisator(
        ...     input_labels=["effort", "encoder", "pixels"], aggregation=[],
        ...     interest_labels=["quality"], output_labels=["log_bitrate"],
        ...     niter=100,  # very little to be fast
        ... ).fit("scatter.db", table="t_enc_encode", select="uniform(vid_hash) >= 0.2")
        >>> pprint(model.psi)
        {(): {'effort': Psi('effort', 3, 7177),
              'encoder': Psi('encoder', 15, 6983),
              'pixels': Psi('pixels', 1, 7095)}}
        >>>

        """
        # verification
        if not self._parameters:
            msg = "before catching psi, you must train the model using the .fit(...) method"
            raise AttributeError(msg)

        # fill attributes
        all_psi: dict[tuple, dict[str, Psi]] = {}
        for clus, (_, _, psi_dict, data) in self._parameters.items():
            all_psi[clus] = all_psi.get(clus, {})
            for lbl, psi in psi_dict.items():
                psi.std_mean = self._std_mean["full"][lbl]
                psi.values = data[lbl]
                all_psi[clus][lbl] = psi
        return all_psi


class TrendEncodeEnergy(TrendNormlisator):
    """Examine the effect of a parameter on encoding time and power.

    This example provides an overview of the effect of quality on energy consumption:

    Examples
    --------
    >>> from mendevi.models.trend import TrendEncodeEnergy
    >>> model = TrendEncodeEnergy(interest_labels=["quality"])
    >>> model = model.fit(
    ...     "scatter.db", table="t_enc_encode", select="uniform(vid_hash) >= 0.2",
    ... )  # doctest: +SKIP
    >>> model.validate(
    ...     "scatter.db", table="t_enc_encode", select="uniform(vid_hash) < 0.2",
    ... )
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
                "nb_frames", "pixels",  # "range", "primaries", "eotf",
                "spatial_dct", "temporal_dct", "rms_sobel", "rms_time_diff",
            ],
        )
        kwargs["output_labels"] = kwargs.get(
            "output_labels",
            ["log_act_duration_per_frame", "power"],
        )
        kwargs["aggregation"] = kwargs.get("aggregation", ["hostname"])
        super().__init__(title=title, **kwargs)
