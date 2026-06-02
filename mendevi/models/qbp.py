"""Predict the encoding energy based on the quality given to the encoder."""

import torch

from .base import Model


class QBP(Model):
    """Quality based prediction of enegy model."""

    def __init__(
        self,
        title: str = "Quality Based Prediction of energy model",
        sources: str = (
            "Modeling The HEVC Encoding Energy Using The Encoder Processing Time\n"
            "Geetha Ramasubbu, André Kaup, Christian Herglotz\n"
            "2022"
        ),
        **kwargs: dict,
    ) -> None:
        """Quality based prediction of enegy model.

        Parameters
        ----------
        title, sources, **kwargs
            Transmitted to :py:class:`mendevi.models.base.Model`.

        """
        kwargs = kwargs.copy()
        kwargs["input_labels"] = kwargs.get("input_labels", ["quality"])
        kwargs["output_labels"] = kwargs.get("output_labels", ["quality"])
        super().__init__(
            title=title,
            sources=sources,
            **kwargs,
        )
        assert "quality" in self.input_labels, self.input_labels
        assert self.output_labels == ["energy"], self.output_labels

    def _fit_vect(self, values: dict[str, torch.Tensor]) -> object:
        """Fit the model E = P*T with T = k*q**3 - l*q**2 - u*q + T0."""
        quality = values["quality"]
        klutp = torch.asarray(
            [8.826, -198.556, 359.969, 181.532, 451.230],  # loss 4.5805e+10
            dtype=quality.dtype, device=quality.device,
            requires_grad=True,
        )
        optim = torch.optim.Adam([klutp], lr=1e-1)
        for _ in range(1000):
            pred_duration = klutp[0]*quality**3 - klutp[1]*quality**2 - klutp[2]*quality + klutp[3]
            pred_energy = klutp[4] * pred_duration
            loss = ((values["energy"] - pred_energy)**2).mean()
            optim.zero_grad()
            loss.backward()
            optim.step()
        return klutp.tolist()

    def _predict_vect(
        self, values: dict[str, torch.Tensor], parameters: object,
    ) -> dict[str, torch.Tensor]:
        """PRediction."""
        quality = values["quality"]
        pred_duration = (
            parameters[0]*quality**3
            - parameters[1]*quality**2
            - parameters[2]*quality
            + parameters[3]
        )
        pred_energy = parameters[4] * pred_duration
        return {"energy": pred_energy}
