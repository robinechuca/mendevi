"""Predict the energy and the quality based on a neuronal network."""


from mendevi.models import Model

import torch


class _TorchNN(torch.nn.Module):
    """Simple perceptron nn."""

    def __init__(self, in_ndim: int, out_ndim: int) -> None:
        assert isinstance(in_ndim, int), in_ndim.__class__.__name__
        assert isinstance(out_ndim, int), out_ndim.__class__.__name__
        super().__init__()
        self.linear = torch.nn.Sequential(
            torch.nn.Linear(in_ndim, 512),
            torch.nn.ReLU(),
            torch.nn.Linear(512, 512),
            torch.nn.ReLU(),
            torch.nn.Linear(512, out_ndim),
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
        # intitialisation
        input_values = torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1)
        reference = torch.cat([values[lbl] for lbl in self.output_labels], dim=1)
        model = _TorchNN(input_values.shape[1], reference.shape[1])

        # train
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        for _ in range(10):
            for _ in range(100):
                optimizer.zero_grad()
                predict = model(input_values)
                loss = torch.mean((predict - reference)**2)
                loss.backward()
                optimizer.step()
            print(loss)

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
