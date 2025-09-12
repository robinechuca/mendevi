#!/usr/bin/env python3

"""Extract the values associated with an axis."""

import numbers

from . import extract


NAMES = [
    "enc_cores",
    "enc_encoder", "encoder",
    "enc_quality", "quality",
    "enc_threads", "threads",
    "profile",
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
        case "enc_cores":
            return (
                "Average cumulative utilisation rate of logic cores during encoding",
                extract.extract_enc_cores,
            )
        case "enc_encoder" | "encoder":
            return (
                "Name of the encoder",
                extract.extract_enc_encoder,
            )
        case "enc_quality" | "quality":
            return (
                "Quality level passed to the encoder",
                extract.extract_enc_quality,
            )
        case "enc_threads" | "threads":
            return (
                "Number of threads provided as a parameter to the encoder",
                extract.extract_enc_threads,
            )
        case "profile":
            return (
                "Profile of the encoded video",
                extract.extract_profile,
            )
