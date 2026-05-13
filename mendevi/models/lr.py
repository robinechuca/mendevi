"""Predicting absolute values using linear regression."""

import torch

from .base import Model


class LinearRegression(Model):
    """Biaised linear regression on all parameters."""

    def __init__(
        self,
        title: str = "Linear Regression for a predictive model",
        sources: str = (
            "A High-Level Feature Model to Predict the Encoding Energy "
            "of a Hardware Video Encoder\n"
            "Diwakara Reddy, Christian Herglotz, and André Kaup\n"
            "2025"
        ),
        *,
        biaised: bool = True,
        **kwargs: dict,
    ) -> None:
        """Gaussian process regression predictive model.

        Parameters
        ----------
        title, sources, **kwargs
            Transmitted to :py:class:`mendevi.models.base.Model`.
        biaised : boolean, default=True
            If True, the linear regression includes a bias term, or y-intercept constant.
            If False, the regression is unbiased, and the y-intercept is zero.

        """
        assert isinstance(biaised, bool), biaised.__class__.__name__
        super().__init__(title=title, sources=sources, **kwargs)
        self._biaised = biaised

    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> object:
        """Perform a linear regression on the centered and reduced values."""
        obs = torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1)
        if self._biaised:
            obs = torch.cat(
                [torch.ones((len(obs), 1), dtype=obs.dtype, device=obs.device), obs], dim=1,
            )
        return {
            response: torch.linalg.pinv(obs.mT @ obs, hermitian=True) @ obs.mT @ values[response]
            for response in self.output_labels
        }

    def _predict_vect_norm(
        self, values: dict[str, torch.Tensor], parameters: object,
    ) -> dict[str, torch.Tensor]:
        obs = torch.cat([values[lbl] for lbl in self.input_labels_aggreg], dim=1)
        if self._biaised:
            obs = torch.cat(
                [torch.ones((len(obs), 1), dtype=obs.dtype, device=obs.device), obs], dim=1,
            )
        return {name: obs @ beta for name, beta in parameters.items()}


class EncodeLinear(LinearRegression):
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
    {'log_act_duration_per_frame': [-1.063035249710083],
     'log_energy_per_frame': [0.5252208709716797],
     'log_rate': [6.431523323059082],
     'psnr': [38.24165725708008],
     'ssim': [0.8785048723220825],
     'vmaf': [81.59996032714844]}
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
