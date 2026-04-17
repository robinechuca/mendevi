"""Predict the energy based on a gaussian process regression.

It commes from the paper:
"A High-Level Feature Model to Predict the Encoding Energy of a Hardware Video Encoder".
"""

import torch

from .base import Model


class GPR(Model):
    """Gaussian process regression on continuous parameters."""

    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> None:
        """Perform a linear regression on the centered and reduced values."""
        # voir https://management-datascience.org/articles/24197/

        MAX_SAMPLES = 4196
        obs = torch.cat([values[lbl][:MAX_SAMPLES] for lbl in self.input_labels], dim=1)
        target = torch.cat([values[lbl][:MAX_SAMPLES] for lbl in self.output_labels], dim=1)

        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
        # kernel = ConstantKernel(1.0) * RBF(length_scale=0.5) + WhiteKernel(noise_level=0.1)
        kernel = RBF(length_scale=0.2) + WhiteKernel(noise_level=0.1)
        gp = GaussianProcessRegressor(
            kernel=kernel,
            alpha=0.0,  # bruit déjà dans le kernel
            n_restarts_optimizer=10,  # éviter les minima locaux
            # normalize_y=True
        )
        gp.fit(obs.numpy(force=True), target.numpy(force=True))

        self.parameters = gp

    def _predict_vect_norm(self, values: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        obs = torch.cat([values[lbl] for lbl in self.input_labels], dim=1)
        pred = torch.from_numpy(
            self.parameters.predict(obs.numpy(force=True))
        ).to(dtype=obs.dtype, device=obs.device)
        return {lbl: pred_[:, None] for lbl, pred_ in zip(self.output_labels, pred.mT)}


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

