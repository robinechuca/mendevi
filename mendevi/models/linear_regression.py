"""Predicting absolute values using linear regression."""

import torch

from .base import Model


class EncodeLinear(Model):
    """Biaised linear regression to predict parameters on encoding.

    Examples
    --------
    >>> import pprint
    >>> import cutcutcodec
    >>> from mendevi.models.linear_regression import EncodeLinear
    >>> model = EncodeLinear().fit("x264_vs_openh264.db", table="t_enc_encode")
    >>> video = cutcutcodec.utils.get_project_root() / "media" / "video" / "intro.webm"
    >>> pred = model.predict_from_video(
    ...     video, effort="medium", encoder="libx264", quality=0.5, threads=8, mode="vbr",
    ... )
    >>> pprint.pprint(pred)
    {'log_act_duration_per_frame': [-0.9902404546737671],
     'log_energy_per_frame': [0.5947314500808716],
     'log_rate': [6.39665412902832],
     'psnr': [37.500999450683594],
     'ssim': [0.8862448334693909],
     'vmaf': [82.45337677001953]}
    >>>

    """

    def __init__(self) -> None:
        """Initialise the model."""
        super().__init__(
            "Linear prediction of video encoding energy and quality.",
            sources="""
            A High-Level Feature Model to Predict the Encoding Energy of a Hardware Video Encoder
            Diwakara Reddy, Christian Herglotz, and André Kaup
            2025
            """,
            input_labels=[
                "effort",
                "encoder",
                "height",
                "mode",
                "quality",
                "rms_sobel",
                "rms_time_diff",
                "threads",
                "width",
            ],
            output_labels=[
                "log_act_duration_per_frame",
                "log_energy_per_frame",
                "log_rate",
                "psnr",
                "ssim",
                "vmaf",
            ],
        )

    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> None:
        """Perform a linear regression on the centered and reduced values."""
        obs = torch.cat([values[lbl] for lbl in self.input_labels], dim=1)
        obs = torch.cat([torch.ones((len(obs), 1), dtype=obs.dtype, device=obs.device), obs], dim=1)
        self.parameters = {
            response: torch.linalg.pinv(obs.mT @ obs, hermitian=True) @ obs.mT @ values[response]
            for response in self.output_labels
        }

    def _predict_vect_norm(self, values: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        obs = torch.cat([values[lbl] for lbl in self.input_labels], dim=1)
        obs = torch.cat([torch.ones((len(obs), 1), dtype=obs.dtype, device=obs.device), obs], dim=1)
        return {name: obs @ beta for name, beta in self.parameters.items()}
