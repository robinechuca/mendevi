"""Predicting absolute values using interpolation."""

import torch

from .base import Model

BUFF_SIZE = 100_000_000  # 100 Mo


class NearestL2(Model):
    """Base class for nearest neighbor interpolation."""

    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> object:
        """Vectorize and save all points."""
        return {
            "obs": torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1),
            "target": torch.cat([values[lbl] for lbl in self.output_labels], dim=1),
        }

    def _predict_vect_norm(
        self, values: dict[str, torch.Tensor], parameters: object,
    ) -> dict[str, torch.Tensor]:
        """Return the closest point according to the l2 distance."""
        obs = torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1)
        dists = ((obs[:, None, :] - parameters["obs"][None, :, :])**2).sum(dim=2)
        best_pred = parameters["target"][dists.argmin(axis=1)]
        return {lbl: best_pred[:, i, None] for i, lbl in enumerate(self.output_labels)}


class EncodeNearest(NearestL2):
    """Model to interpolate parameters on encoding.

    Examples
    --------
    >>> import pprint
    >>> import cutcutcodec
    >>> from mendevi.models.interp import EncodeNearest
    >>> model = EncodeNearest().fit("x264_vs_openh264.db", table="t_enc_encode")
    >>> video = cutcutcodec.utils.get_project_root() / "media" / "video" / "intro.webm"
    >>> pred = model.predict_from_video(
    ...     video, effort="medium", encoder="libx264", quality=0.5, threads=8, mode="vbr",
    ... )
    >>> pprint.pprint(pred)
    {'log_act_duration_per_frame': [-1.6198468208312988],
     'log_energy_per_frame': [-0.006180912256240845],
     'log_rate': [5.841528415679932],
     'psnr': [39.743228912353516],
     'ssim': [0.9432291388511658],
     'vmaf': [94.80208587646484]}
    >>>

    """

    def __init__(self) -> None:
        """Initialise the model."""
        super().__init__(
            "Nearest interpolation of video encoding energy and quality.",
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
