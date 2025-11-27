#!/usr/bin/env python3

"""Help to get the good extractor."""

import ast
import collections
import enum
import importlib
import pathlib
import tempfile
import typing
import uuid

import networkx as nx

from mendevi.database import extract


class Scale(enum.Flag):
    """The axis type."""
    LINEAR = enum.auto()
    LOGARITHMIC = enum.auto()
    DISCRETE = enum.auto()


class ExtractContext(collections.abc.Mapping):
    """Correctly define a variable in a context.

    Examples
    --------
    >>> from mendevi.database.meta import Scale, ExtractContext
    >>> ExtractContext("legend", "func", Scale.DISCRETE)
    ExtractContext('legend', 'func', Scale.DISCRETE)
    >>> {**_}
    {'legend': 'legend', 'func': 'func', 'scale': <Scale.DISCRETE: 4>}
    >>>
    """

    def __init__(self, legend: str, func: typing.Callable | str, scale: Scale):
        """Create a dictlike named tuple."""
        assert isinstance(legend, str), legend.__class__.__name__
        assert callable(func) or isinstance(func, str), func.__class__.__name__
        assert isinstance(scale, Scale), scale.__class__.__name__
        self._legend, self._func, self._scale = legend, func, scale

    @property
    def legend(self) -> str:
        """The description."""
        return self._legend

    @property
    def func(self) -> typing.Callable | str:
        """The function or the expression to compute the variable."""
        return self._func

    @property
    def scale(self) -> Scale:
        """The kind of variable."""
        return self._scale

    def __getitem__(self, item: str) -> object:
        """Return the attribute."""
        return {
            "legend": self._legend,
            "func": self._func,
            "scale": self._scale,
        }[item]

    def __iter__(self) -> tuple:
        """Yield the keys."""
        yield from ("legend", "func", "scale")

    def __len__(self) -> int:
        """The numbers of attributes."""
        return 3

    def __repr__(self) -> str:
        """Return a nice representation."""
        return f"{self.__class__.__name__}({self._legend!r}, {self._func!r}, {self._scale})"


def _import_extractor(code: list[str]) -> callable:
    """Import the function line_extractor."""
    code = [
        "from mendevi.utils import best_profile",
        "import mendevi.database.extract as extract",
        "",
        *code,
    ]
    path = pathlib.Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}.py"
    with path.open("w", encoding="utf-8") as file:
        file.write("\n".join(code))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    modulevar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulevar)
    path.unlink()
    return modulevar.line_extractor


def _print_branch(leaf: str, skip: set[str], graph: nx.DiGraph) -> list[str]:
    """Return the code to extract a branch."""
    branch_code: list[str] = []
    predecessors = {leaf} - skip
    while predecessors:
        skip |= predecessors
        for lbl in sorted(predecessors):  # sorted for reproductibility and lisibility
            legend, func = graph.nodes[lbl]["legend"], graph.nodes[lbl]["func"]
            branch_code.insert(
                0,
                (
                    f"    {lbl} = extract.{func.__name__}(raw)  # {legend}"
                    if callable(func) else
                    f"    {lbl} = {func}  # {legend}"
                ),
            )
        predecessors = {pp for p in predecessors for pp in graph.predecessors(p)} - skip
    return branch_code


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
        msg = f"the argument {expr!r} is not a valid python expression"
        raise SyntaxError(
            msg,
        ) from err
    reject = {
        n.id for n in nodes if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store | ast.Del)
    } | {
        n_.id
        for n in nodes if isinstance(n, ast.Call) and not isinstance(n.func, ast.Attribute)
        for n_ in ast.walk(n.func) if isinstance(n_, ast.Name)
    }
    candidates = {n.id for n in nodes if isinstance(n, ast.Name)}
    return set(candidates - reject)  # set usefull for empty case


def get_extractor(name: str, *, safe: bool = False) -> ExtractContext:
    """Get the way to deserialize a raw value.

    Parameters
    ----------
    name : str
        The label name.
    safe : boolean, default=False
        If True, retrun a stupid value instead of raising KeyError.

    Returns
    -------
    extractor : ExtractContext
        The label, func and scale.

    """
    assert isinstance(name, str), name.__class__.__name__
    assert isinstance(safe, bool), safe.__class__.__name__
    extractor = None
    match name:  # catched by mendevi.cst.labels.extract_labels
        case "act_duration":
            return ExtractContext(
                "Video processing activity duration in seconds",
                extract.extract_act_duration,
                Scale.LINEAR,
            )
        case "bitrate" | "rate":
            return ExtractContext(
                r"Video bitrate in $bit.s^{-1}$",
                "None if size is None or video_duration is None else 8.0 * size / video_duration",
                Scale.LOGARITHMIC,
            )
        case "codec":
            return ExtractContext(
                "Codec name",
                extract.extract_codec,
                Scale.DISCRETE,
            )
        case "cores":
            return ExtractContext(
                "Average cumulative utilisation rate of logical cores",
                extract.extract_cores,
                Scale.LINEAR,
            )
        case "decode_cmd" | "dec_cmd":
            return ExtractContext(
                "The ffmpeg command used for decoding",
                extract.extract_decode_cmd,
                Scale.DISCRETE,
            )
        case "decode_scenario" | "dec_scenario":
            return ExtractContext(
                "Unique string specific to the decoding scenario",
                'f"cmd: {decode_cmd}, hostname: {hostname}"',
                Scale.DISCRETE,
            )
        case "effort" | "preset":
            return ExtractContext(
                "Effort provided as a parameter to the encoder",
                extract.extract_effort,
                Scale.DISCRETE,
            )
        case "encode_cmd" | "enc_cmd":
            return ExtractContext(
                "The ffmpeg command used for encoding",
                extract.extract_encode_cmd,
                Scale.DISCRETE,
            )
        case "encode_scenario" | "enc_scenario":
            return ExtractContext(
                "Unique string specific to the encoding scenario",
                'f"cmd: {encode_cmd}, video_name: {video_name}, hostname: {hostname}"',
                Scale.DISCRETE,
            )
        case "encoder":
            return ExtractContext(
                "Name of the encoder",
                extract.extract_encoder,
                Scale.DISCRETE,
            )
        case "energy":
            return ExtractContext(
                "Total energy consumption in Joules",
                "float((powers[0] * powers[1]).sum())",
                Scale.LOGARITHMIC,
            )
        case "energy_per_frame":
            return ExtractContext(
                "Average energy consumption per frame in Joules",
                "energy / nbr_frames",
                Scale.LOGARITHMIC,
            )
        case "frames":
            extractor = ExtractContext(
                "The metadata of each frame",
                extract.extract_frames,
                Scale.DISCRETE,
            )
        case "height":
            extractor = ExtractContext(
                "Height of images in pixels",
                extract.extract_height,
                Scale.LINEAR,
            )
        case "gamut" | "prim" | "primaries" | "color_primaries":
            extractor = ExtractContext(
                "The tristimulus primaries colors name",
                extract.extract_gamut,
                Scale.DISCRETE,
            )
        case "hostname":
            extractor = ExtractContext(
                "The machine name",
                extract.extract_hostname,
                Scale.DISCRETE,
            )
        case "lpips":
            extractor = ExtractContext(
                "Learned Perceptual Image Patch Similarity (LPIPS)",
                extract.extract_lpips,
                Scale.LINEAR,
            )
        case "lpips_alex":
            extractor = ExtractContext(
                "Learned Perceptual Image Patch Similarity (LPIPS) with alex",
                extract.extract_lpips_alex,
                Scale.LINEAR,
            )
        case "lpips_vgg":
            extractor = ExtractContext(
                "Learned Perceptual Image Patch Similarity (LPIPS) with vgg",
                extract.extract_lpips_vgg,
                Scale.LINEAR,
            )
        case "power":
            extractor = ExtractContext(
                "Average power consumption in Watts",
                "energy / float(powers[0].sum())",
                Scale.LINEAR,
            )
        case "powers":
            extractor = ExtractContext(
                "The interval duration and the average power in each intervals",
                extract.extract_powers,
                Scale.DISCRETE,
            )
        case "mode":
            extractor = ExtractContext(
                "Bitrate mode, constant (cbr) or variable (vbr)",
                extract.extract_mode,
                Scale.DISCRETE,
            )
        case "nb_frames" | "nbr_frames":
            extractor = ExtractContext(
                "The real number of frames of the video file",
                "len(frames)",
                Scale.LOGARITHMIC,
            )
        case "profile":
            extractor = ExtractContext(
                "Profile of the video",
                (
                    "None if height is None and width is None else "
                    "best_profile(height or width, width or height)"
                ),
                Scale.DISCRETE,
            )
        case "psnr":
            extractor = ExtractContext(
                "Peak Signal to Noise Ratio (PSNR)",
                extract.extract_psnr,
                Scale.LINEAR,
            )
        case "quality":
            extractor = ExtractContext(
                "Quality level passed to the encoder",
                extract.extract_quality,
                Scale.LINEAR,
            )
        case "range":
            extractor = ExtractContext(
                "Video encoding color range, 'tv' or 'pc'",
                extract.extract_range,
                Scale.DISCRETE,
            )
        case (
            "reference_video_name" | "reference_vid_name" | "reference_name"
            | "ref_video_name" | "ref_vid_name" | "ref_name"
        ):
            extractor = ExtractContext(
                "Input video basename",
                extract.extract_reference_video_name,
                Scale.DISCRETE,
            )
        case "rms_sobel":
            extractor = ExtractContext(
                "Spacial root mean square sobel gradient complexity",
                extract.extract_rms_sobel,
                Scale.LINEAR,
            )
        case "rms_time_diff":
            extractor = ExtractContext(
                "Temporal root means square time difference complexity",
                extract.extract_rms_time_diff,
                Scale.LINEAR,
            )
        case "shape":
            extractor = ExtractContext(
                "The image shapes height x width in pixels",
                "(height, width)",
                Scale.DISCRETE,
            )
        case "ssim":
            extractor = ExtractContext(
                "Structural Similarity (SSIM)",
                extract.extract_ssim,
                Scale.LINEAR,
            )
        case "ssim_comp" | "comp_ssim" | "ssim_rev" | "rev_ssim":
            extractor = ExtractContext(
                "Complementary of Structural Similarity (1-SSIM)",
                "1.0 - ssim",
                Scale.LOGARITHMIC,
            )
        case "threads":
            extractor = ExtractContext(
                "Number of threads provided as a parameter to the encoder",
                extract.extract_threads,
                Scale.LINEAR,
            )
        case "transfer" | "trans" | "color_transfer" | "eotf":
            extractor = ExtractContext(
                "The non-linear transfer function name",
                extract.extract_transfer,
                Scale.DISCRETE,
            )
        case "vmaf":
            extractor = ExtractContext(
                "Video Multi-Method Assessment Fusion (VMAF)",
                extract.extract_vmaf,
                Scale.LINEAR,
            )
        case "video_duration" | "vid_duration":
            extractor = ExtractContext(
                "Video duration in seconds",
                extract.extract_video_duration,
                Scale.LINEAR,
            )
        case "video_hash" | "vid_hash" | "video_md5" | "vid_md5":
            extractor = ExtractContext(
                "The hexadecimal md5 video file checksum",
                extract.extract_video_hash,
                Scale.DISCRETE,
            )
        case "video_name" | "vid_name" | "name":
            extractor = ExtractContext(
                "Video basename",
                extract.extract_video_name,
                Scale.DISCRETE,
            )
        case "video_size" | "vid_size" | "size":
            extractor = ExtractContext(
                "The total video file size in bytes",
                extract.extract_video_size,
                Scale.LOGARITHMIC,
            )
        case "width":
            extractor = ExtractContext(
                "Width of images in pixels",
                extract.extract_height,
                Scale.LINEAR,
            )
    if extractor is not None:
        return extractor
    if safe:
        return ExtractContext(name, name, Scale.LINEAR)
    msg = f"{name} is not recognised"
    raise KeyError(msg)


def merge_extractors(
    labels: set[str],
    alias: dict[str, str] | None = None,
    select: str | None = None,
    *,
    return_callable: bool = False,
) -> tuple[set[str], list[str] | typing.Callable]:
    r'''Return the source code of the function that extracts all variables.

    Parameters
    ----------
    labels : set[str]
        The returned variable names. These are the keys to the output dictionary.
    alias : dict[str, str], optional
        To each new name, associate an expression.
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
    >>> labels = {"enc_scenario", "rate", "power", "foo"}
    >>> alias = {"foo": "(abaca, energy)", "abaca": "(hostname, nbr_frames, enc_scenario)"}
    >>> select = '"yeti" not in hostname'
    >>> print("\n".join(merge_extractors(labels, alias, select)[1]))  # doctest: +ELLIPSIS
    def line_extractor(raw: dict[str]) -> dict[str]:
        """Get the labels: enc_scenario, foo, power, rate.

        Causality constraint:
            * enc_scenario -> abaca
            * encode_cmd -> enc_scenario
            * hostname -> enc_scenario
            * hostname -> reject
            * hostname -> abaca
            * video_name -> enc_scenario
            * size -> rate
            * video_duration -> rate
            * abaca -> foo
            * energy -> foo
            * energy -> power
            * powers -> power
            * powers -> energy
            * nbr_frames -> abaca
            * frames -> nbr_frames
        """
        # reject wrong line
        hostname = extract.extract_hostname(raw)  # The machine name
        reject = not ("yeti" not in hostname)  # not ("yeti" not in hostname)
        if reject:
            raise RejectError("this line must be filtered")

        # extract data
        video_name = extract.extract_video_name(raw)  # Video basename
        encode_cmd = extract.extract_encode_cmd(raw)  # The ffmpeg command used for encoding
        enc_scenario = f"cmd: {encode_cmd}, video_name: {video_name}, hostname: {hostname}"  # Un...
        frames = extract.extract_frames(raw)  # The metadata of each frame
        powers = extract.extract_powers(raw)  # The interval duration and the average power in ea...
        nbr_frames = len(frames)  # The real number of frames of the video file
        energy = float((powers[0] * powers[1]).sum())  # Total energy consumption in Joules
        abaca = (hostname, nbr_frames, enc_scenario)  # (hostname, nbr_frames, enc_scenario)
        foo = (abaca, energy)  # (abaca, energy)
        power = energy / float(powers[0].sum())  # Average power consumption in Watts
        video_duration = extract.extract_video_duration(raw)  # Video duration in seconds
        size = extract.extract_video_size(raw)  # The total video file size in bytes
        rate = None if size is None or video_duration is None else 8.0 * size / video_duration  #...

        return {
            'enc_scenario': enc_scenario,
            'rate': rate,
            'foo': foo,
            'power': power,
        }
    >>>

    '''
    assert isinstance(labels, set), labels.__class__.__name__
    assert all(isinstance(lbl, str) for lbl in labels), labels
    alias = alias or {}
    assert isinstance(alias, dict), alias.__class__.__name__
    assert select is None or isinstance(select, str), select.__class__.__name__

    extractors = nx.DiGraph()

    # initialise the graph with final leaves
    for label in labels:
        extractors.add_node(label, **get_extractor(alias.get(label, label), safe=True))
    # extractors.add_nodes_from(labels)  # adding leaves
    if select is not None:
        extractors.add_node(
            "reject", **get_extractor(f"not ({alias.get(select, select)})", safe=True),
        )

    # construct the full tree
    while nodes := [
        n for n, deg in extractors.in_degree()
        if deg == 0 and not callable(extractors.nodes[n]["func"])
    ]:
        for node in nodes:
            for root in extract_names(alias.get(node, extractors.nodes[node]["func"])):
                extractors.add_node(root, **get_extractor(alias.get(root, root), safe=True))
                extractors.add_edge(root, node)

    # # draw graph for debug: sudo apt install graphviz graphviz-dev && uv pip install pygraphviz
    # with open("/tmp/extractors.dot", "w") as file:
    #     for node in extractors:
    #         extractors.nodes[node]["label"] = (
    #             f"{node}\\n{'\\n'.join(f'{k}:{v!r}' for k, v in extractors.nodes[node].items())}"
    #         )
    #     file.write(nx.nx_agraph.to_agraph(extractors).string())

    # verification of undefinded variable or cycle
    if cycles := list(nx.simple_cycles(extractors)):
        msg = (
            f"The extraction graph has cycles: {cycles}, "
            "which means that variables are not defined. "
            "You must specify an alias to break all cycles."
        )
        raise ValueError(msg)

    # create the source code
    # 1) header
    code = [
        "def line_extractor(raw: dict[str]) -> dict[str]:",
        f'    """Get the labels: {", ".join(sorted(labels))}.',
        "",
        "    Causality constraint:",
        *(f"        * {prev} -> {node}" for prev, node in extractors.edges),
        '    """',
    ]
    skip: set[str] = set()  # processed nodes

    # 2) reject bad line
    if select is not None:
        code.extend([
            "    # reject wrong line",
            *_print_branch("reject", skip, extractors),
            "    if reject:",
            '        raise RejectError("this line must be filtered")',
            "",
        ])

    # 3) extract the tree for all labels
    code.extend([
        "    # extract data",
        *(line for leaf in sorted(labels) for line in _print_branch(leaf, skip, extractors)),
        "",
    ])

    # 4) cast and return the values
    code.extend([
        "    return {",
        *(f"        {lbl!r}: {lbl}," for lbl in labels),
        "    }",
    ])

    # import source code
    return (
        {n for n in extractors if callable(extractors.nodes[n]["func"])},
        (_import_extractor(code) if return_callable else code),
    )
