"""Predict the energy and the quality based on a neuronal network."""

import typing

import torch
import tqdm
from context_verbose import Printer

from .base import EPS, Model, discard_nan


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

    def __init__(self, niter: int=10000, rate: float=1e-4, **kwargs: dict) -> None:
        """Define the gradient decrease convergence parameters.

        Parameters
        ----------
        **kwargs
            Transmitted to :py:class:`mendevi.models.base.Model`.
        niter : int, default=1000
            The number of epoch, also the number of batch, because one batch by epoch.
        rate : float, default=1e-3
            The learning rate.

        """
        assert isinstance(niter, int), niter.__class__.__name__
        assert niter >= 0, niter
        assert isinstance(rate, float), rate.__class__.__name__
        assert rate > 0, rate
        self._niter, self._rate = niter, rate
        super().__init__(**kwargs)

    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> object:
        """Perform the gradient descent on a just intanciated nn."""
        # intitialisation
        input_values = torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1)
        reference = torch.cat([values[lbl] for lbl in self.output_labels], dim=1)

        # handle nan values
        nanmask = ~input_values.isnan().any(dim=1)  # to discarded corrupted input
        input_values, nanref = input_values[nanmask, :], reference[nanmask, :]
        nanmask = nanref.isnan()  # for output

        # end of initialization
        total = max(
            input_values.shape[1] + 8 + nanref.shape[1],  # minimum structural
            input_values.shape[0] // 5,  # empirical rule
        )
        model = _TorchNN(input_values.shape[1], nanref.shape[1], total=total)

        # train
        model.train()
        optimizer = torch.optim.RAdam(model.parameters(), lr=self._rate)
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
    >>> from mendevi.models.dnn import QualityNN
    >>> model = QualityNN(output_labels=["psnr", "log_rev_ssim"])
    >>> model.fit("svtav1_vs_rav1e_vs_aom.db", select="uniform(vid_hash) >= 0.2")
    >>> model.validate("svtav1_vs_rav1e_vs_aom.db", select="uniform(vid_hash) < 0.2")
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


class KernelMultiHead(DNN):
    """Share the kernel NN to all aggregated data, and split output with several headers."""

    def _fit_vect(self, values: dict[str, torch.Tensor]) -> object:
        """Hack to delay the model instantation and training."""
        return values  # no normalization to avoid a subnormalisation by cluster

    def _delay_fit(self) -> tuple:
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
            lr=self._rate,
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
                    + 0.1 * identity_regularization  # force latent space to be homogeneous
                ).backward()
                optimizer.step()
                progress_bar.update(1)
        # sum up
        for lbl in sorted(losses):
            prt.print(f"mse {lbl}: {losses[lbl]:9.3e}")
        prt.print_time()


        # import matplotlib.pyplot as plt
        # for lbl, (idx_min, idx_max) in slices.items():
        #     plt.xlabel(f"{lbl} intrinsec")
        #     plt.ylabel(f"{lbl} absolute")
        #     for clus, trans in heads.items():
        #         trad_model = trans[lbl]
        #         mini, maxi = model(parameters[clus]["input"])[:, idx_min:idx_max].aminmax()
        #         plt.plot(
        #             (
        #                 torch.linspace(mini, maxi, 1000) * self._std_mean["full"][lbl][0]
        #                 + self._std_mean["full"][lbl][1]
        #             ).numpy(force=True).ravel(),
        #             (
        #                 (
        #                     torch.linspace(mini, maxi, 1000)[:, None]
        #                     + trad_model(torch.linspace(mini, maxi, 1000)[:, None])
        #                 )
        #                 * self._std_mean["full"][lbl][0] + self._std_mean["full"][lbl][1]
        #             ).numpy(force=True).ravel(),
        #             label=str(clus),
        #         )
        #     plt.legend()
        #     plt.show()

        return (model, slices, heads)


    def fit(self, *args: tuple, **kwargs: dict) -> typing.Self:
        """Container for the :py:meth:`Model.fit` method."""
        super().fit(*args, **kwargs)  # prepare data
        self._parameters = self._delay_fit()  # create and train all models



class EncodeEnergyNN(KernelMultiHead):
    """Deep neuronal network for the video encoding energy prediction.

    Examples
    --------
    >>> from mendevi.models.dnn import EncodeEnergyNN
    >>> model = EncodeEnergyNN().fit("svtav1_vs_rav1e_vs_aom.db", table="t_enc_encode")
    >>> model.delay_fit()
    >>> model.validate("svtav1_vs_rav1e_vs_aom.db")
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
    >>> from mendevi.models.dnn import DecodeEnergyNN
    >>> model = DecodeEnergyNN().fit("svtav1_vs_rav1e_vs_aom.db", table="t_dec_decode")
    >>> model.validate("svtav1_vs_rav1e_vs_aom.db")
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
