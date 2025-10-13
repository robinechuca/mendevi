#!/usr/bin/env python3

"""Help to get the good extractor."""

import ast
import collections
import typing

from mendevi.database import extract


ExtractContext = collections.namedtuple("ExtractContext", ["label", "func", "is_log"])


def extract_names(expr: str) -> set[str]:
    """Return all the symbols in the python expression.

    Examples
    --------
    >>> from mendevi.database.meta import extract_names
    >>> extract_names('foo')
    {'foo'}
    >>> extract_names('[i**2 for i in foo]')
    {'foo'}
    >>> extract_names('foo.bar')
    {'foo'}
    >>> extract_names('bar(foo)')
    {'foo'}
    """
    nodes = [n for n in ast.walk(ast.parse(expr, mode="exec"))]
    reject = {
        n.id for n in nodes if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store | ast.Del)
    } | {
        n_.id
        for n in nodes if isinstance(n, ast.Call)
        for n_ in ast.walk(n.func) if isinstance(n_, ast.Name)
    }
    keep = {n.id for n in nodes if isinstance(n, ast.Name)}
    names = set(keep - reject)  # set usefull for empty case
    return names


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
    func : callable | str
        The function that performs the verification and deserialisation task,
        or the formula that allows you to find this quantity.
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
                "8.0 * size / video_duration",
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
        case "nb_frames" | "nbr_frames":
            return ExtractContext(
                "The real number of frames of the video file",
                extract.extract_nb_frames,
                True,
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
        case "ssim_comp" | "comp_ssim" | "ssim_rev" | "rev_ssim":
            return ExtractContext(
                "Complementary of Structural Similarity (1-SSIM)",
                extract.extract_ssim_comp,
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
        case "video_size" | "vid_size" | "size":
            return ExtractContext(
                "The total video file size in bytes",
                extract.extract_video_size,
                True,
            )
    raise KeyError(f"{name} is not recognised")


def merge_extractors(labels: set[str], select: typing.Optional[str] = None) -> ast.Module:
    r'''Return the source code of the function that extracts all variables.

    Examples
    --------
    >>> from mendevi.database.meta import merge_extractors
    >>> print("\n".join(merge_extractors({"rate", "profile"})[1]))
    def line_extractor(raw: dict[str]) -> dict[str]:
    """Get the labels: profile, rate."""
        # deserialisation of basic values
        profile = extract.extract_profile(raw)
        size = extract.extract_video_size(raw)
        video_duration = extract.extract_video_duration(raw)
    <BLANKLINE>
        # association of basic values
        rate = 8.0 * size / video_duration
    <BLANKLINE>
        # packaging
        return {
            'profile': profile
            'rate': rate
        }
    >>>
    '''
    assert isinstance(labels, set), labels.__class__.__name__
    assert all(isinstance(lbl, str) for lbl in labels), labels.__class__.__name__
    if select is not None:
        assert isinstance(select, str), select.__class__.__name__

    def get_atom_tree(labels: set[str]) -> tuple[set[str], list[str]]:
        """Return the minimalist labels name and the way to associate them."""
        lbl_atom: set[str] = set()  # all atomic symbols
        tree: list[str] = []  # intermediate symbols, in the correct order
        lbl_func = {l: get_extractor(l).func for ls in labels for l in extract_names(ls)}
        while lbl_func:
            lbl_atom |= {l for l, f in lbl_func.items() if callable(f)}
            tree = sorted(lbl for lbl in lbl_func if lbl not in lbl_atom) + tree
            lbl_func = {
                l: get_extractor(l).func
                for ls in lbl_func.values() if isinstance(ls, str)
                for l in extract_names(ls)
            }
        return lbl_atom, tree

    # selector
    if select is not None:
        select_lbl_atom, tree = get_atom_tree(extract_names(select))
        check_lines = [
            "    # exit if data are undesirable",
            *(
                f"    {lbl} = extract.{get_extractor(lbl).func.__name__}(raw)"
                for lbl in sorted(select_lbl_atom)
            ),
            *(f"    {lbl} = {get_extractor(lbl).func}" for lbl in tree),
            f"    if not ({select}):",
            '        raise RejectError("this line must be filtered")',
            "",
        ]
    else:
        check_lines = []

    # final code, all together
    lbl_atom, tree = get_atom_tree(labels)
    code = [
        "def line_extractor(raw: dict[str]) -> dict[str]:",
        f'    """Get the labels: {", ".join(sorted(labels))}."""',
        *check_lines,
        "    # extract revelant values",
        *(
            f"    {lbl} = extract.{get_extractor(lbl).func.__name__}(raw)"
            for lbl in sorted(lbl_atom - select_lbl_atom)  # limit redundancy
        ),
        *(f"    {lbl} = {get_extractor(lbl).func}" for lbl in tree),
        "",
        "    # packaging",
        "    return {",
        *(f"        {lbl!r}: {lbl}," for lbl in sorted(labels)),
        "    }"
    ]
    return lbl_atom, code
