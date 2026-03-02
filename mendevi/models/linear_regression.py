"""Predicting absolute values using linear regression."""

import torch

from .base import Model


class LinearFull(Model):
    """Biaised linear regression on all parameters."""

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


class LinearContinuous(Model):
    """Biaised linear regression on continuous parameters."""

    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> None:
        """Vectorize and save all points."""
        onehot_lbls: list[str] = [lbl for lbl in self.input_labels if values[lbl].shape[1] != 1]
        onehots: list[tuple[int, ...]] | torch.Tensor = list(map(  # all ordered keys
            tuple,
            (torch.cat([values[lbl] for lbl in onehot_lbls], dim=1) + 0.5)
            .to(dtype=int)  # values are assumed to be approximately {0.0, 1.0}
            .tolist(),
        ))
        onehot_to_idx: dict[tuple[int, ...], int] = {
            onehot: i for i, onehot in enumerate(sorted(set(onehots)))
        }
        continuous_lbls: list[str] = [lbl for lbl in self.input_labels if lbl not in onehot_lbls]
        continuous = torch.cat([values[lbl] for lbl in continuous_lbls], dim=1)
        onehots = torch.asarray([onehot_to_idx[onehot] for onehot in onehots], dtype=int)
        onehot_to_obs: dict[tuple[int, ...], torch.Tensor] = {
            onehot: continuous[onehots == idx, :]
            for onehot, idx in onehot_to_idx.items()
        }
        onehot_to_obs = {
            onehot: torch.cat([torch.ones((len(obs), 1), dtype=obs.dtype, device=obs.device), obs], dim=1)
            for onehot, obs in onehot_to_obs.items()
        }
        onehot_to_output: dict[tuple[int, ...], dict[str, torch.Tensor]] = {
            onehot: {lbl: values[lbl][onehots == idx, :] for lbl in self.output_labels}
            for onehot, idx in onehot_to_idx.items()
        }

        linear_weight: dict[tuple[int, ...], dict[str, torch.Tensor]] = {
            onehot: {  # TODO, ajouter un biais (des 1) a obs
                lbl: torch.linalg.pinv(obs.mT @ obs, hermitian=True) @ obs.mT @ onehot_to_output[onehot][lbl]
                for lbl in self.output_labels
            }
            for onehot, obs in onehot_to_obs.items()
        }

        self.parameters = {
            "onehot_lbls": onehot_lbls,  # list[str] the ordered onehot input names
            "continuous_lbls": continuous_lbls,  # list[str] the ordered coninuous input names
            "linear_weight": linear_weight,
        }

    def _predict_vect_norm(self, values: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        all_obs = torch.cat([values[lbl] for lbl in self.parameters["continuous_lbls"]], dim=1)
        all_obs = torch.cat(
            [torch.ones((len(all_obs), 1), dtype=all_obs.dtype, device=all_obs.device), all_obs],
            dim=1,
        )
        relbeta_relobs: list[tuple[dict[str, torch.Tensor], int]] = [
            (
                self.parameters["linear_weight"][onehot],
                obs[None, :],
            )
            for onehot, obs in zip(
                map(
                    tuple,
                    (torch.cat([values[lbl] for lbl in self.parameters["onehot_lbls"]], dim=1) + 0.5)
                    .to(dtype=int)  # values are assumed to be approximately {0.0, 1.0}
                    .tolist(),
                ),
                all_obs,
            )
        ]
        return {
            lbl: torch.cat([(obs @ beta[lbl]) for beta, obs in relbeta_relobs], dim=0)
            for lbl in self.output_labels
        }


class EncodeLinear(LinearContinuous):
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
