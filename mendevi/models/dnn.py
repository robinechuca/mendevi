"""Predict the energy and the quality based on a neuronal network."""


from mendevi.models import Model

import torch


class _TorchNN(torch.nn.Module):
    """Simple perceptron nn."""

    def __init__(self, ndim: int):
        super().__init__()
        self.linear = nn.Sequential(
            nn.Linear(ndim, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, ndim),
        )

    def forward(self, values: torch.Tensor):
        """Inference of the vectorised model.

        Parameters
        ----------
        values : torch.Tensor
            The concatenated values of shape (batch, ndim)
        """
        assert isinstance(values, torch.Tensor), values.__class__.__name__
        assert values.ndim == 2, values.shape
        return self.linear(values)


class DNN(Model):
    """Deep neuronal network predictive model.

    Examples
    --------
    >>> from mendevi.models.dnn import DNN
    >>> model = DNN().fit("<multithread.db>", table="t_enc_encode")
    >>> model.predict(["paradoxe-32.rennes.grid5000.fr"], [0.0])
    >>>

    """

    def __init__(
        self,
        title: str = "Energy and Quality estimation based on a neuronal network",
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
            "output_labels", [
                "act_duration_per_frame", "power", "size_per_frame",
                "lpips", "psnr", "ssim", "vmaf",
            ],
        )
        kwargs["aggregation"] = ["hostname"]  # the only non interpolable parameter
        super().__init__(title=title, **kwargs)

    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> object:
        """Perform the gradient descent on a juste intanciated nn."""
        import ipdb; ipdb.set_trace()
        raise NotImplementedError

    def _predict_vect_norm(
        self, values: dict[str, torch.Tensor], parameters: object,
    ) -> dict[str, torch.Tensor]:
        """Inference part of the model."""
        raise NotImplementedError
