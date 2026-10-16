# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Predict the energy based on a gaussian process regression.

It commes from the paper:
"A High-Level Feature Model to Predict the Encoding Energy of a Hardware Video Encoder".

https://www.infinitecuriosity.org/vizgp/
https://hannibunny.github.io/mlbook/machinelearning/GaussianProcessRegression.html
https://management-datascience.org/articles/24197/
https://labex.io/fr/tutorials/gaussian-process-regression-and-classification-71104
"""

import torch
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

from .base import Model


class GPR(Model):
    """Gaussian process regression on continuous parameters."""

    def __init__(
        self,
        title: str = "Gaussian Process Regression predictive model",
        nu_kernel: float = 0.5,
        sources: str = (
            "A High-Level Feature Model to Predict the Encoding Energy "
            "of a Hardware Video Encoder\n"
            "Diwakara Reddy, Christian Herglotz, and André Kaup\n"
            "2025"
        ),
        **kwargs: dict,
    ) -> None:
        r"""Gaussian process regression predictive model.

        Parameters
        ----------
        title, sources, \*\*kwargs
            Transmitted to :py:class:`mendevi.models.base.Model`.
        nu_kernel : float, default = 0.5
            The parameter $\nu$ of the Matern kernel.
            The default value match the paper absolute exponential kernel.
            An other nice value is 1.5 with is smoother and gives better predictions.

        """
        assert isinstance(nu_kernel, float), nu_kernel.__class__.__name__
        super().__init__(title=title, sources=sources, **kwargs)
        self._kernel = ConstantKernel() * Matern(nu=nu_kernel) + WhiteKernel()

    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> object:
        """Perform a linear regression on the centered and reduced values."""
        max_samples = 1024  # 2048 -> 2h
        obs = torch.cat([values[lbl][:max_samples] for lbl in self.input_labels_aggreg], dim=1)
        target = torch.cat([values[lbl][:max_samples] for lbl in self.output_labels], dim=1)

        gpr = GaussianProcessRegressor(
            kernel=self._kernel,
            alpha=1e-8,  # to help numerical stability
            n_restarts_optimizer=10,  # like in the paper
            normalize_y=False,
        )
        gpr.fit(obs.numpy(force=True), target.numpy(force=True))
        # print(f"optimized kernel: {gpr.kernel_}")
        return gpr

    def _predict_vect_norm(
        self, values: dict[str, torch.Tensor], parameters: object,
    ) -> dict[str, torch.Tensor]:
        obs = torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1)
        pred = torch.from_numpy(
            parameters.predict(obs.numpy(force=True)),
        ).to(dtype=obs.dtype, device=obs.device)
        return {lbl: pred_[:, None] for lbl, pred_ in zip(self.output_labels, pred.mT, strict=True)}


# class EncodeGPR(GPR):
#     """Biaised linear regression to predict parameters on encoding.

#     Examples
#     --------
#     >>> import pprint
#     >>> import cutcutcodec
#     >>> from mendevi.models.gpr import EncodeGPR
#     >>> model = EncodeGPR().fit("x264_vs_openh264.db", table="t_enc_encode")
#     >>> video = cutcutcodec.utils.get_project_root() / "media" / "video" / "intro.webm"
#     >>> pred = model.predict_from_video(
#     ...     video, effort="medium", encoder="libx264", quality=0.5, threads=8, mode="crf",
#     ... )
#     >>> pprint.pprint(pred)
#     {'log_act_duration_per_frame': [-1.1730448007583618],
#      'log_energy_per_frame': [0.3901517987251282],
#      'log_rate': [6.401565074920654],
#      'psnr': [36.51514434814453],
#      'ssim': [0.905691921710968],
#      'vmaf': [86.33578491210938]}
#     >>>

#     """

#     def __init__(self) -> None:
#         """Initialise the model."""
#         super().__init__(
#             input_labels=[
#                 "effort",
#                 "encoder",
#                 "height",
#                 "mode",
#                 "quality",
#                 "rms_sobel",
#                 "rms_time_diff",
#                 "threads",
#                 "width",
#             ],
#             output_labels=[
#                 "log_act_duration_per_frame",
#                 "log_energy_per_frame",
#                 "log_rate",
#                 "psnr",
#                 # "ssim",
#                 # "vmaf",
#             ],
#         )
