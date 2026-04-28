"""Predict the energy based on a gaussian process regression.

It commes from the paper:
"A High-Level Feature Model to Predict the Encoding Energy of a Hardware Video Encoder".

https://www.infinitecuriosity.org/vizgp/
https://hannibunny.github.io/mlbook/machinelearning/GaussianProcessRegression.html
https://management-datascience.org/articles/24197/
https://labex.io/fr/tutorials/gaussian-process-regression-and-classification-71104
"""

import torch

from .base import Model


class GPR(Model):
    """Gaussian process regression on continuous parameters."""

    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> object:
        """Perform a linear regression on the centered and reduced values."""
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, WhiteKernel

        max_samples = 1024  # 2048 -> 2h
        obs = torch.cat([values[lbl][:max_samples] for lbl in self.input_labels_aggreg], dim=1)
        target = torch.cat([values[lbl][:max_samples] for lbl in self.output_labels], dim=1)

        kernel = RBF(length_scale=0.2) + WhiteKernel(noise_level=0.1)
        gpr = GaussianProcessRegressor(
            kernel=kernel,
            alpha=0.0,  # noise already included in the kernel
            n_restarts_optimizer=10,  # like in the paper
            normalize_y=False,
        )
        gpr.fit(obs.numpy(force=True), target.numpy(force=True))
        return gpr

    def _predict_vect_norm(
        self, values: dict[str, torch.Tensor], parameters: object,
    ) -> dict[str, torch.Tensor]:
        obs = torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1)
        pred = torch.from_numpy(
            parameters.predict(obs.numpy(force=True)),
        ).to(dtype=obs.dtype, device=obs.device)
        return {lbl: pred_[:, None] for lbl, pred_ in zip(self.output_labels, pred.mT, strict=True)}


class EncodeGPR(GPR):
    """Biaised linear regression to predict parameters on encoding.

    Examples
    --------
    >>> import pprint
    >>> import cutcutcodec
    >>> from mendevi.models.gpr import EncodeGPR
    >>> model = EncodeGPR().fit("x264_vs_openh264.db", table="t_enc_encode")
    >>> video = cutcutcodec.utils.get_project_root() / "media" / "video" / "intro.webm"
    >>> pred = model.predict_from_video(
    ...     video, effort="medium", encoder="libx264", quality=0.5, threads=8, mode="vbr",
    ... )
    >>> pprint.pprint(pred)
    {'log_act_duration_per_frame': [-1.1730448007583618],
     'log_energy_per_frame': [0.3901517987251282],
     'log_rate': [6.401565074920654],
     'psnr': [36.51514434814453],
     'ssim': [0.905691921710968],
     'vmaf': [86.33578491210938]}
    >>>

    """

    def __init__(self) -> None:
        """Initialise the model."""
        super().__init__(
            "GPR prediction of video encoding energy and quality.",
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
                # "ssim",
                # "vmaf",
            ],
        )

