#!/usr/bin/env python3

"""Extract the values associated with an axis."""

import numbers

from . import extract


NAMES = [
    "cores",
    "act_duration",
    "effort", "preset",
    "encoder",
    "quality",
    "enc_scenario",
    "threads",
    "wattmeter_energy", "energy",
    "wattmeter_power", "power",
    "profile",
    "rate", "bitrate",
    "src_vid",
    "psnr",
    "ssim",
    "vmaf",
    "lpips", "lpips_alex", "lpips_vgg",
]


def get_label_extractor(name: str):
    """Get the way to deserialize a raw value.

    Parameters
    ----------
    name : str
        The value code, one of :py:cst`mendevi.plot.axis.NAMES`.

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
    match name:
        case "cores":
            return (
                "Average cumulative utilisation rate of logical cores",
                extract.extract_cores,
                False,
            )
        case "effort" | "preset":
            return (
                "Effort provided as a parameter to the encoder",
                extract.extract_effort,
                None,
            )
        case "act_duration":
            return (
                "Video processing activity duration in seconds",
                extract.extract_act_duration,
                False,
            )
        case "encoder":
            return (
                "Name of the encoder",
                extract.extract_encoder,
                None,
            )
        case "quality":
            return (
                "Quality level passed to the encoder",
                extract.extract_quality,
                False,
            )
        case "enc_scenario":
            return (
                "Unique string specific to the encoding scenario",
                extract.extract_enc_scenario,
                None,
            )
        case "threads":
            return (
                "Number of threads provided as a parameter to the encoder",
                extract.extract_threads,
                False,
            )
        case "wattmeter_energy" | "energy":
            return (
                "Total energy consumption in Joules",
                extract.extract_wattmeter_energy,
                True,
            )
        case "wattmeter_power" | "power":
            return (
                "Average power consumption in Watts",
                extract.extract_wattmeter_power,
                False,
            )
        case "profile":
            return (
                "Profile of the video",
                extract.extract_profile,
                None,
            )
        case "rate" | "bitrate":
            return (
                "Video bitrate in bit per seconds",
                extract.extract_bitrate,
                True,
            )
        case "src_vid":
            return (
                "Input video name",
                extract.extract_src_vid,
                None,
            )
        case "psnr":
            return (
                "Peak Signal to Noise Ratio (PSNR)",
                extract.extract_psnr,
                False,
            )
        case "ssim":
            return (
                "Structural Similarity (SSIM)",
                extract.extract_ssim,
                False,
            )
        case "vmaf":
            return (
                "Video Multi-Method Assessment Fusion (VMAF)",
                extract.extract_vmaf,
                False,
            )
        case "lpips_alex":
            return (
                "Learned Perceptual Image Patch Similarity (LPIPS) with alex",
                extract.extract_lpips_alex,
                False,
            )
        case "lpips_vgg":
            return (
                "Learned Perceptual Image Patch Similarity (LPIPS) with vgg",
                extract.extract_lpips_vgg,
                False,
            )
        case "lpips":
            return (
                "Learned Perceptual Image Patch Similarity (LPIPS)x",
                extract.extract_lpips,
                False,
            )
