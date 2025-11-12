#!/usr/bin/env python3

"""Help to get the good extractor."""

import ast
import collections
import importlib
import pathlib
import tempfile
import uuid

from mendevi.database import extract

ExtractContext = collections.namedtuple("ExtractContext", ["label", "func", "is_log"])


def extract_names(expr: str) -> set[str]:
    """Return all the symbols in the python expression.

    Examples
    --------
    >>> from mendevi.database.meta import extract_names
    >>> extract_names("foo")
    {'foo'}
    >>> extract_names("[i**2 for i in foo]"")
    {'foo'}
    >>> extract_names("foo.bar")
    {'foo'}
    >>> extract_names("bar(foo)")
    {'foo'}
    >>> extract_names("foo.bar()")
    {'foo'}
    >>>

    """
    try:
        nodes = list(ast.walk(ast.parse(expr, mode="exec")))
    except SyntaxError as err:
        raise SyntaxError(
            f"the argument {expr!r} is not a valid python expression",
        ) from err
    reject = {
        n.id for n in nodes if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store | ast.Del)
    } | {
        n_.id
        for n in nodes if isinstance(n, ast.Call) and not isinstance(n.func, ast.Attribute)
        for n_ in ast.walk(n.func) if isinstance(n_, ast.Name)
    }
    candidates = {n.id for n in nodes if isinstance(n, ast.Name)}
    names = set(candidates - reject)  # set usefull for empty case
    return names


def get_extractor(name: str, safe: bool = False) -> ExtractContext:
    """Get the way to deserialize a raw value.

    Parameters
    ----------
    name : str
        The label name.
    safe : boolean, default=False
        If True, retrun a stupid value instead of raising KeyError.

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
    assert isinstance(safe, bool), safe.__class__.__name__
    extractor = None
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
                "None if size is None or video_duration is None else 8.0 * size / video_duration",
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
        case "decode_cmd" | "dec_cmd":
            return ExtractContext(
                "The ffmpeg command used for decoding",
                extract.extract_decode_cmd,
                None,
            )
        case "decode_scenario" | "dec_scenario":
            return ExtractContext(
                "Unique string specific to the decoding scenario",
                'f"cmd: {decode_cmd}, hostname: {hostname}"',
                None,
            )
        case "effort" | "preset":
            return ExtractContext(
                "Effort provided as a parameter to the encoder",
                extract.extract_effort,
                None,
            )
        case "encode_cmd" | "enc_cmd":
            return ExtractContext(
                "The ffmpeg command used for encoding",
                extract.extract_encode_cmd,
                None,
            )
        case "encode_scenario" | "enc_scenario":
            return ExtractContext(
                "Unique string specific to the encoding scenario",
                'f"cmd: {encode_cmd}, video_name: {video_name}, hostname: {hostname}"',
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
                "float((powers[0] * powers[1]).sum())",
                True,
            )
        case "energy_per_frame":
            return ExtractContext(
                "Average energy consumption per frame in Joules",
                "energy / nbr_frames",
                True,
            )
        case "frames":
            extractor = ExtractContext(
                "The metadata of each frame",
                extract.extract_frames,
                None,
            )
        case "height":
            extractor = ExtractContext(
                "Height of images in pixels",
                extract.extract_height,
                False,
            )
        case "gamut" | "prim" | "primaries" | "color_primaries":
            extractor = ExtractContext(
                "The tristimulus primaries colors name",
                extract.extract_gamut,
                None,
            )
        case "hostname":
            extractor = ExtractContext(
                "The machine name",
                extract.extract_hostname,
                None,
            )
        case "lpips":
            extractor = ExtractContext(
                "Learned Perceptual Image Patch Similarity (LPIPS)",
                extract.extract_lpips,
                False,
            )
        case "lpips_alex":
            extractor = ExtractContext(
                "Learned Perceptual Image Patch Similarity (LPIPS) with alex",
                extract.extract_lpips_alex,
                False,
            )
        case "lpips_vgg":
            extractor = ExtractContext(
                "Learned Perceptual Image Patch Similarity (LPIPS) with vgg",
                extract.extract_lpips_vgg,
                False,
            )
        case "power":
            extractor = ExtractContext(
                "Average power consumption in Watts",
                "energy / float(powers[0].sum())",
                False,
            )
        case "powers":
            extractor = ExtractContext(
                "The interval duration and the average power in each intervals",
                extract.extract_powers,
                None,
            )
        case "mode":
            extractor = ExtractContext(
                "Bitrate mode, constant (cbr) or variable (vbr)",
                extract.extract_mode,
                None,
            )
        case "nb_frames" | "nbr_frames":
            extractor = ExtractContext(
                "The real number of frames of the video file",
                "len(frames)",
                True,
            )
        case "profile":
            extractor = ExtractContext(
                "Profile of the video",
                (
                    "None if height is None and width is None else "
                    "best_profile(height or width, width or height)"
                ),
                None,
            )
        case "psnr":
            extractor = ExtractContext(
                "Peak Signal to Noise Ratio (PSNR)",
                extract.extract_psnr,
                False,
            )
        case "quality":
            extractor = ExtractContext(
                "Quality level passed to the encoder",
                extract.extract_quality,
                False,
            )
        case "range":
            extractor = ExtractContext(
                "Video encoding color range, 'tv' or 'pc'",
                extract.extract_range,
                None,
            )
        case "shape":
            extractor = ExtractContext(
                "The image shapes height x width in pixels",
                "(height, width)",
                None,
            )
        case "ssim":
            extractor = ExtractContext(
                "Structural Similarity (SSIM)",
                extract.extract_ssim,
                False,
            )
        case "ssim_comp" | "comp_ssim" | "ssim_rev" | "rev_ssim":
            extractor = ExtractContext(
                "Complementary of Structural Similarity (1-SSIM)",
                "1.0 - ssim",
                True,
            )
        case "threads":
            extractor = ExtractContext(
                "Number of threads provided as a parameter to the encoder",
                extract.extract_threads,
                False,
            )
        case "transfer" | "trans" | "color_transfer" | "eotf":
            extractor = ExtractContext(
                "The non-linear transfer function name",
                extract.extract_transfer,
                None,
            )
        case "vmaf":
            extractor = ExtractContext(
                "Video Multi-Method Assessment Fusion (VMAF)",
                extract.extract_vmaf,
                False,
            )
        case "video_duration" | "vid_duration":
            extractor = ExtractContext(
                "Video duration in seconds",
                extract.extract_video_duration,
                False,
            )
        case "video_hash" | "vid_hash" | "video_md5" | "vid_md5":
            extractor = ExtractContext(
                "The hexadecimal md5 video file checksum",
                extract.extract_video_hash,
                None,
            )
        case "video_name" | "vid_name" | "name":
            extractor = ExtractContext(
                "Input video basename",
                extract.extract_video_name,
                None,
            )
        case "video_size" | "vid_size" | "size":
            extractor = ExtractContext(
                "The total video file size in bytes",
                extract.extract_video_size,
                True,
            )
        case "width":
            extractor = ExtractContext(
                "Width of images in pixels",
                extract.extract_height,
                False,
            )
    if extractor is not None:
        return extractor
    if safe:
        return ExtractContext(name, name, False)
    raise KeyError(f"{name} is not recognised")


def merge_extractors(
    labels: set[str],
    alias: dict[str, str] | None = None,
    select: str | None = None,
    return_callable: bool = False,
) -> tuple[set[str]]:
    r'''Return the source code of the function that extracts all variables.

    Parameters
    ----------
    labels : set[str]
        The returned variable names. These are the keys to the output dictionary.
    alias : dict[str, str], optional
        By default, the label extraction method is defined by the function :py:func:`get_extractor`.
        This list of aliases allows any unknown key to define a customised access method.
    select : str, optional
        A Python Boolean expression that raises a RejectError exception if it evaluates to False.
    return_callable : boolean, default=False
        By default, returns the source code of the function.
        If this option is set to True, an executable function is returned.

    Returns
    -------
    lbls_atom : set[str]
        The name of the primary value to be extracted for the SQL query.
    func : list[str] or callable
        The function that consumes a line from the SQL query,
        and returns the dictionary of extracted values.

    Examples
    --------
    >>> from mendevi.database.meta import merge_extractors
    >>> print("\n".join(merge_extractors({"rate", "enc_scenario"}, select="'yeti' in hostname")[1]))
    def line_extractor(raw: dict[str]) -> dict[str]:
        """Get the labels: enc_scenario, rate, reject."""
        hostname = extract.extract_hostname(raw)
        reject = not ('yeti' in hostname)
        if reject:
            raise RejectError("this line must be filtered")
        encode_cmd = extract.extract_encode_cmd(raw)
        size = extract.extract_video_size(raw)
        video_name = extract.extract_video_name(raw)
        video_duration = extract.extract_video_duration(raw)
        enc_scenario = f"cmd: {encode_cmd}, video_name: {video_name}, hostname: {hostname}"
        rate = None if size is None or video_duration is None else 8.0 * size / video_duration
        return {
            'enc_scenario': enc_scenario,
            'rate': rate,
            'reject': reject,
        }

    '''
    assert isinstance(labels, set), labels.__class__.__name__
    assert all(isinstance(lbl, str) for lbl in labels), labels.__class__.__name__
    alias = (alias or {}).copy()
    assert isinstance(alias, dict), alias.__class__.__name__
    assert all(isinstance(k, str) for k in alias), alias
    assert "reject" not in alias, "'reject' is a forbidden key for 'alias'"
    if select is not None:
        assert isinstance(select, str), select.__class__.__name__

    # recursively extracts all steps
    # 1) initialisation of the tree leaves
    for lbl in labels:
        alias[lbl] = alias.get(lbl, get_extractor(lbl).func)
    labels = sorted(alias)
    if select is not None:
        alias["reject"] = f"not ({select})"
    # 2) recursive exploration of the tree to find the roots
    leaves = {leave for leave, expr in alias.items() if not callable(expr)}
    while leaves:
        new_alias = {
            lbl: get_extractor(lbl).func
            for branch in leaves
            for lbl in extract_names(alias[branch]) if lbl not in alias
        }
        alias |= new_alias
        leaves = {leave for leave, expr in new_alias.items() if not callable(expr)}
    # 3) keep all roots in meomry
    lbls_atom = {root for root, func in alias.items() if callable(func)}

    # organising lines in the correct order
    def get_roots(alias: dict[str], leave: str) -> str:
        """Explore the tree and return a root."""
        if callable(alias[leave]):
            yield leave
        elif subtree := {
            root
            for lbl in extract_names(alias[leave]) if lbl in alias
            for root in get_roots(alias, lbl)
        }:
            yield from sorted(subtree)
        else:  # case not callable but not subtree ever
            yield leave

    # 1) extract 'reject' first, go strait on it
    tree: list[tuple[str, str]] = []  # orderd dict
    while "reject" in alias:
        root = next(iter(get_roots(alias, "reject")))
        tree.append((root, alias.pop(root)))
    # 2) extract the others
    while alias:
        for lbl in labels:
            if lbl in alias:
                root = next(iter(get_roots(alias, lbl)))
                tree.append((root, alias.pop(root)))

    # print the main functions
    code = [
        "def line_extractor(raw: dict[str]) -> dict[str]:",
        f'    """Get the labels: {", ".join(sorted(labels))}."""',
    ]
    for lbl, func in tree:
        if callable(func):
            code.append(f"    {lbl} = extract.{func.__name__}(raw)")
        else:
            code.append(f"    {lbl} = {func}")
        if lbl == "reject":
            code.extend([
                "    if reject:",
                '        raise RejectError("this line must be filtered")',
            ])
    code.extend([
        "    return {",
        *(f"        {lbl!r}: {lbl}," for lbl in labels),
        "    }",
    ])
    if not return_callable:
        return lbls_atom, code

    # import the source code as a function
    code = [
        "from mendevi.utils import best_profile",
        "import mendevi.database.extract as extract",
        "",
        *code,
    ]
    path = pathlib.Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}.py"
    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(code))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    modulevar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulevar)
    path.unlink()
    return lbls_atom, modulevar.line_extractor
