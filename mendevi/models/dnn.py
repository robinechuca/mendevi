"""Predict the energy and the quality based on a neuronal network."""


from mendevi.models import Model

import torch
import tqdm


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

    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> object:
        """Perform the gradient descent on a just intanciated nn."""
        # intitialisation
        input_values = torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1)
        reference = torch.cat([values[lbl] for lbl in self.output_labels], dim=1)
        total = max(
            input_values.shape[1] + 8 + reference.shape[1],  # minimum structural
            input_values.shape[0] // 5,  # empirical rule
        )
        model = _TorchNN(input_values.shape[1], reference.shape[1], total=total)

        # train
        model.train()
        optimizer = torch.optim.Adam(model.parameters(), lr=2e-4)
        iterations = 10_000
        with tqdm.tqdm(
            desc="Gradient decay",
            dynamic_ncols=True,
            leave=False,
            smoothing=1e-6,
            total=iterations,
        ) as progress_bar:
            for _ in range(iterations):
                optimizer.zero_grad()
                predict = model(input_values)
                loss = torch.mean((predict - reference)**2)
                loss.backward()
                optimizer.step()
                progress_bar.update(1)
                progress_bar.set_postfix_str(f"loss: {loss:9.3e}")
        model.eval()

        # serialisation
        return (model, {lbl: values[lbl].shape[1] for lbl in self.output_labels})

    def _predict_vect_norm(
        self, values: dict[str, torch.Tensor], parameters: object,
    ) -> dict[str, torch.Tensor]:
        """Inference part of the model."""
        # preparation, vectorisation
        input_values = torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1)
        model, sizes = parameters

        # inference
        prediction = model(input_values)

        # parse result
        output = {}
        index = 0
        for lbl in self.output_labels:
            output[lbl] = prediction[:, index:index+sizes[lbl]]
            index += sizes[lbl]
        return output


# from mendevi.models.dnn import DNN_Quality
# DNN_Quality().fit("/data/dataset/merge.db", table="t_met_metric", select="lpips is not None and uniform(vid_hash) > 0.2").validate("/data/dataset/merge.db", table="t_met_metric", select="lpips is not None and uniform(vid_hash) <= 0.2")
class DNN_Quality(DNN):
    """Deep neuronal network for the video quality prediction.

    Examples
    --------
    >>> from mendevi.models.dnn import DNN_Quality
    >>> model = DNN_Quality(output_labels=["psnr", "log_rev_ssim"])
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
            ["lpips", "psnr", "ssim", "vmaf", "log_size_per_frame"],
        )
        kwargs["aggregation"] = kwargs.get("aggregation", [])
        super().__init__(title=title, **kwargs)


class DNN_EncodeEnergy(DNN):
    """Deep neuronal network for the video encoding energy prediction.

    Examples
    --------
    >>> from mendevi.models.dnn import DNN_EncodeEnergy
    >>> model = DNN_EncodeEnergy().fit("svtav1_vs_rav1e_vs_aom.db", table="t_enc_encode")
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
        kwargs["output_labels"] = kwargs.get("output_labels", ["log_act_duration_per_frame", "power"])
        kwargs["aggregation"] = kwargs.get("aggregation", ["hostname"])
        super().__init__(title=title, **kwargs)


class DNN_DecodeEnergy(DNN):
    """Deep neuronal network for the video encoding energy prediction.

    Examples
    --------
    >>> from mendevi.models.dnn import DNN_DecodeEnergy
    >>> model = DNN_DecodeEnergy().fit("svtav1_vs_rav1e_vs_aom.db", table="t_dec_decode")
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
        kwargs["output_labels"] = kwargs.get("output_labels", ["log_act_duration_per_frame", "power"])
        kwargs["aggregation"] = kwargs.get("aggregation", ["hostname"])
        super().__init__(title=title, **kwargs)



