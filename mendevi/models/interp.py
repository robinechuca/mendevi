"""Predicting absolute values using interpolation."""

import torch

from .base import Model

BUFF_SIZE = 100_000_000  # 100 Mo


class Nearest(Model):
    """Base class for nearest neighbor interpolation.

    Interpolation is only performed on continuous values.
    """

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
        onehot_to_continuous: dict[tuple[int, ...], torch.Tensor] = {
            onehot: continuous[onehots == idx, :]
            for onehot, idx in onehot_to_idx.items()
        }
        onehot_to_output: dict[tuple[int, ...], dict[str, torch.Tensor]] = {
            onehot: {lbl: values[lbl][onehots == idx, :] for lbl in self.output_labels}
            for onehot, idx in onehot_to_idx.items()
        }
        self.parameters = {
            "onehot_lbls": onehot_lbls,  # list[str] the ordered onehot input names
            "continuous_lbls": continuous_lbls,  # list[str] the ordered coninuous input names
            "onehot_to_continuous": onehot_to_continuous,  # continuous input subclusters
            "output": oonehot_to_utput,
        }

    def _predict_vect_norm(self, values: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        """Return the closest point according to the l2 distance."""
        reloutput_relidxs: list[tuple[dict[str, torch.Tensor], int]] = [
            (
                self.parameters["output"][onehot],  # subcluster corresponding to the correct onehot
                (  # index of the closest input value within this continuous cluster
                    ((continuous[None, :] - self.parameters["onehot_to_continuous"][onehot])**2)
                    .sum(dim=1)
                    .argmin(dim=0)
                    .item()
                ),
            )
            for onehot, continuous in zip(
                map(
                    tuple,
                    (torch.cat([values[lbl] for lbl in self.parameters["onehot_lbls"]], dim=1) + 0.5)
                    .to(dtype=int)  # values are assumed to be approximately {0.0, 1.0}
                    .tolist(),
                ),
                torch.cat([values[lbl] for lbl in self.parameters["continuous_lbls"]], dim=1),
            )
        ]
        return {
            lbl: torch.cat([out[lbl][idx, None, :] for out, idx in reloutput_relidxs], dim=0)
            for lbl in self.output_labels
        }


class EncodeNearest(Nearest):
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
