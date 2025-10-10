#!/usr/bin/env python3

"""Help to get the good extractor."""

import collections

from mendevi.database import extract


ExtractContext = collections.namedtuple("ExtractContext", ["label", "func", "is_log"])


def get_extractor(name: str):
    """Get the way to deserialize a raw value.

    Parameters
    ----------
    name : str
        The label name.

    Returns
    -------
    label : str
        The description of the physical quantity.
        This description can be used to label the axes of a graph.
    func : callable
        The function that performs the verification and deserialisation task.
    is_log : boolean or None
        True to display in log space, False for linear.
        The value None means the axis is not continuous.
    """
    assert isinstance(name, str), name.__class__.__name__
    match name:  # catched by mendevi.cst.labels.extract_labels
        case "act_duration":
            return ExtractContext(
                "Video processing activity duration in seconds",
                extract.extract_act_duration,
                False,
            )
        case "bitrate" | "rate":
            return ExtractContext(
                r"Video bitrate in $bit.s^{-1}$",
                extract.extract_bitrate,
                True,
            )
        case "codec":
            return ExtractContext(
                "Codec name",
                extract.extract_codec,
                None,
            )
        case "cores":
            return ExtractContext(
                "Average cumulative utilisation rate of logical cores",
                extract.extract_cores,
                False,
            )
        case "effort" | "preset":
            return ExtractContext(
                "Effort provided as a parameter to the encoder",
                extract.extract_effort,
                None,
            )
        case "enc_scenario":
            return ExtractContext(
                "Unique string specific to the encoding scenario",
                extract.extract_enc_scenario,
                None,
            )
        case "encoder":
            return ExtractContext(
                "Name of the encoder",
                extract.extract_encoder,
                None,
            )
        case "energy":
            return ExtractContext(
                "Total energy consumption in Joules",
                extract.extract_energy,
                True,
            )
        case "lpips":
            return ExtractContext(
                "Learned Perceptual Image Patch Similarity (LPIPS)",
                extract.extract_lpips,
                False,
            )
        case "lpips_alex":
            return ExtractContext(
                "Learned Perceptual Image Patch Similarity (LPIPS) with alex",
                extract.extract_lpips_alex,
                False,
            )
        case "lpips_vgg":
            return ExtractContext(
                "Learned Perceptual Image Patch Similarity (LPIPS) with vgg",
                extract.extract_lpips_vgg,
                False,
            )
        case "power":
            return ExtractContext(
                "Average power consumption in Watts",
                extract.extract_power,
                False,
            )
        case "mode":
            return ExtractContext(
                "Bitrate mode, constant (cbr) or variable (vbr)",
                extract.extract_mode,
                None,
            )
        case "profile":
            return ExtractContext(
                "Profile of the video",
                extract.extract_profile,
                None,
            )
        case "psnr":
            return ExtractContext(
                "Peak Signal to Noise Ratio (PSNR)",
                extract.extract_psnr,
                False,
            )
        case "quality":
            return ExtractContext(
                "Quality level passed to the encoder",
                extract.extract_quality,
                False,
            )
        case "ssim":
            return ExtractContext(
                "Structural Similarity (SSIM)",
                extract.extract_ssim,
                False,
            )
        case "ssim_rev" | "rev_ssim":
            return ExtractContext(
                "Reverse of Structural Similarity (1-SSIM)",
                extract.extract_ssim_rev,
                True,
            )
        case "threads":
            return ExtractContext(
                "Number of threads provided as a parameter to the encoder",
                extract.extract_threads,
                False,
            )
        case "vmaf":
            return ExtractContext(
                "Video Multi-Method Assessment Fusion (VMAF)",
                extract.extract_vmaf,
                False,
            )
        case "video_duration" | "vid_duration":
            return ExtractContext(
                "Video duration in seconds",
                extract.extract_video_duration,
                False,
            )
        case "video_name" | "vid_name" | "name":
            return ExtractContext(
                "Input video name",
                extract.extract_video_name,
                None,
            )
    raise KeyError(f"{name} is not recognised")
