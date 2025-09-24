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
    # "src_vid",
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
    """
    assert isinstance(name, str), name.__class__.__name__
    match name:
        case "cores":
            return (
                "Average cumulative utilisation rate of logical cores",
                extract.extract_cores,
            )
        case "effort" | "preset":
            return (
                "Effort provided as a parameter to the encoder",
                extract.extract_effort,
            )
        case "act_duration":
            return (
                "Video processing activity duration in seconds",
                extract.extract_act_duration,
            )
        case "encoder":
            return (
                "Name of the encoder",
                extract.extract_encoder,
            )
        case "quality":
            return (
                "Quality level passed to the encoder",
                extract.extract_quality,
            )
        case "enc_scenario":
            return (
                "Unique string specific to the encoding scenario",
                extract.extract_enc_scenario,
            )
        case "threads":
            return (
                "Number of threads provided as a parameter to the encoder",
                extract.extract_threads,
            )
        case "wattmeter_energy" | "energy":
            return (
                "Total energy consumption in Joules",
                extract.extract_wattmeter_energy,
            )
        case "wattmeter_power" | "power":
            return (
                "Average power consumption in Watts",
                extract.extract_wattmeter_power,
            )
        case "profile":
            return (
                "Profile of the video",
                extract.extract_profile,
            )
        # case "src_vid":
        #     return (
        #         "Input video name",
        #         extract.extract_src_vid,
        #     )
