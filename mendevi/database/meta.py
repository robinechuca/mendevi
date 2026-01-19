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
    """Represent the nature of the variable, continuous or discrete."""

    LINEAR = enum.auto()
    LOGARITHMIC = enum.auto()
    DISCRETE = enum.auto()


class Extractor(collections.abc.Mapping):
    """Correctly define a variable in a context.

    Examples
    --------
    >>> from mendevi.database.meta import Scale, Extractor
    >>> Extractor("legend", "func", Scale.DISCRETE)
    Extractor('legend', 'func', Scale.DISCRETE)
    >>> {**_}
    {'legend': 'legend', 'func': 'func', 'scale': <Scale.DISCRETE: 4>}
    >>>

    """

    def __init__(self, legend: str, func: typing.Callable | str, scale: Scale) -> None:
        """Create a dictlike named tuple."""
        assert isinstance(legend, str), legend.__class__.__name__
        assert callable(func) or isinstance(func, str), func.__class__.__name__
        assert isinstance(scale, Scale), scale.__class__.__name__
        self._legend, self._func, self._scale = legend, func, scale

    @property
    def legend(self) -> str:
        """Return the description."""
        return self._legend

    @property
    def func(self) -> typing.Callable | str:
        """Return the function or the expression to compute the variable."""
        return self._func

    @property
    def scale(self) -> Scale:
        """Return the kind of variable."""
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
        """Return the numbers of attributes."""
        return 3

    def __repr__(self) -> str:
        """Return a nice representation."""
        return f"{self.__class__.__name__}({self._legend!r}, {self._func!r}, {self._scale})"


ALL_EXTRACTORS = {
    "act_duration": Extractor(
        "Video processing activity duration in seconds",
        extract.extract_act_duration,
        Scale.LINEAR,
    ),
    "bitrate": Extractor(
        r"Video bitrate in $bit.s^{-1}$",
        "None if size is None or video_duration is None else 8.0 * size / video_duration",
        Scale.LOGARITHMIC,
    ),
    "category": Extractor(
        "3GPP TR 26.955, 5G Video Codec Characteristics",
        (
            "{\n"
            '    "aov": "Gaming",\n'  # ; Key: S5-R01",\n'
            '    "baolei_balloon": "Gaming",\n'  # ; Key: S5-R04",\n'
            '    "baolei_man": "Gaming",\n'  # ; Key: S5-R02",\n'
            '    "baolei_woman": "Gaming",\n'  # ; Key: S5-R03",\n'
            '    "baolei_yard": "Gaming",\n'  # ; Key: S5-R05",\n'
            '    "boat": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "bode_museum": "8K-TV",\n'  # ; Key: S3-R16",\n'
            '    "brest_sedof": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "cosmos": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "cs_go": "Gaming",\n'  # ; Key: S5-R12",\n'
            '    "elevator": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "fountain": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "graphics_mix_simple": "ScreenContent",\n'  # ; Key: S3-R09",\n'
            '    "graphics_mix_transitions": "ScreenContent",\n'  # ; Key: S3-R13",\n'
            '    "heroes_of_the_storm": "Gaming",\n'  # ; Key: S5-R08",\n'
            '    "jianling_beach": "Gaming",\n'  # ; Key: S5-R07",\n'
            '    "jianling_temple": "Gaming",\n'  # ; Key: S5-R06",\n'
            '    "life_untouched": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "meridian": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "mine_craft": "Gaming",\n'  # ; Key: S5-R11",\n'
            '    "mission_control": "ScreenContent",\n'  # ; Key: S3-R17",\n'
            '    "mooving_text": "ScreenContent",\n'  # ; Key: S3-R01",\n'
            '    "neon": "Messaging",\n'  # ; Key: S3-R16",\n'
            '    "neptune_fountain_2": "8K-TV",\n'  # ; Key: S3-R16",\n'
            '    "neptune_fountain_3": "8K-TV",\n'  # ; Key: S3-R16",\n'
            '    "nocturne": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "oberbaum_spree": "8K-TV",\n'  # ; Key: S3-R16",\n'
            '    "park_joy": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "project_cars": "Gaming",\n'  # ; Key: S5-R09",\n'
            '    "quadriga_tree": "8K-TV",\n'  # ; Key: S3-R16",\n'
            '    "rain_fruits": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "riverbank": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "skater": "Messaging",\n'  # ; Key: S3-R16",\n'
            '    "soccer": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "sol_levante": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "sparks": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "star_craft": "Gaming",\n'  # ; Key: S5-R13",\n'
            '    "subway_tree": "8K-TV",\n'  # ; Key: S3-R16",\n'
            '    "text_mix_transition": "ScreenContent",\n'  # ; Key: S3-R05",\n'
            '    "tiergarten_parkway": "8K-TV",\n'  # ; Key: S3-R16",\n'
            '    "tunnel_flag": "4K-TV",\n'  # ; Key: S5-R5",\n'
            '    "world_of_warcraft": "Gaming",\n'  # ; Key: S5-R10",\n'
            "}.get(reference_video_stem, reference_video_stem)"
        ),
        Scale.DISCRETE,
    ),
    "codec": Extractor(
        "Codec name",
        extract.extract_codec,
        Scale.DISCRETE,
    ),
    "cores": Extractor(
        "Average cumulative utilisation rate of logical cores",
        extract.extract_cores,
        Scale.LINEAR,
    ),
    "decode_cmd": Extractor(
        "The ffmpeg command used for decoding",
        extract.extract_decode_cmd,
        Scale.DISCRETE,
    ),
    "decode_ram": Extractor(
        "Is the decoded video stored in RAM?",
        '"yes" if "/dev/shm" in decode_cmd else "no"',
        Scale.DISCRETE,
    ),
    "decode_scenario": Extractor(
        "Unique string specific to the decoding scenario",
        'f"cmd: {decode_cmd}, hostname: {hostname}"',
        Scale.DISCRETE,
    ),
    "decoder": Extractor(
        "Name of the decoder",
        extract.extract_decoder,
        Scale.DISCRETE,
    ),
    "decoder_family": Extractor(
        "The type of decoder",
        '"cuvid" if str(decoder).endswith("_cuvid") else "cpu"',
        Scale.DISCRETE,
    ),
    "effort": Extractor(
        "Effort provided as a parameter to the encoder",
        extract.extract_effort,
        Scale.DISCRETE,
    ),
    "encode_cmd": Extractor(
        "The ffmpeg command used for encoding",
        extract.extract_encode_cmd,
        Scale.DISCRETE,
    ),
    "encode_ram": Extractor(
        "Is the encoded video stored in RAM?",
        '"yes" if "/dev/shm" in encode_cmd else "no"',
        Scale.DISCRETE,
    ),
    "encode_scenario": Extractor(
        "Unique string specific to the encoding scenario",
        'f"cmd: {encode_cmd}, video_name: {video_name}, hostname: {hostname}"',
        Scale.DISCRETE,
    ),
    "encoder": Extractor(
        "Name of the encoder",
        extract.extract_encoder,
        Scale.DISCRETE,
    ),
    "encoder_family": Extractor(
        "The type of encoder",
        '"nvenc" if str(encoder).endswith("_nvenc") else "cpu"',
        Scale.DISCRETE,
    ),
    "energy": Extractor(
        "Total energy consumption in Joules",
        "None if powers is None else float((powers[0] * powers[1]).sum())",
        Scale.LOGARITHMIC,
    ),
    "energy_per_frame": Extractor(
        "Average energy consumption per frame in Joules",
        "None if energy is None or nbr_frames is None else energy / nbr_frames",
        Scale.LOGARITHMIC,
    ),
    "frames": Extractor(
        "The metadata of each frame",
        extract.extract_frames,
        Scale.DISCRETE,
    ),
    "gamut": Extractor(
        "The tristimulus primaries colors name",
        extract.extract_gamut,
        Scale.DISCRETE,
    ),
    "height": Extractor(
        "Height of images in pixels",
        extract.extract_height,
        Scale.LINEAR,
    ),
    "hostname": Extractor(
        "The machine name",
        extract.extract_hostname,
        Scale.DISCRETE,
    ),
    "lpips": Extractor(
        "Learned Perceptual Image Patch Similarity (LPIPS)",
        extract.extract_lpips,
        Scale.LINEAR,
    ),
    "lpips_alex": Extractor(
        "Learned Perceptual Image Patch Similarity (LPIPS) with alex",
        extract.extract_lpips_alex,
        Scale.LINEAR,
    ),
    "lpips_vgg": Extractor(
        "Learned Perceptual Image Patch Similarity (LPIPS) with vgg",
        extract.extract_lpips_vgg,
        Scale.LINEAR,
    ),
    "power": Extractor(
        "Average power consumption in Watts",
        "None if energy is None or powers is None else energy / float(powers[0].sum())",
        Scale.LINEAR,
    ),
    "powers": Extractor(
        "The interval duration and the average power in each intervals",
        extract.extract_powers,
        Scale.DISCRETE,
    ),
    "mode": Extractor(
        "Bitrate mode, constant (cbr) or variable (vbr)",
        extract.extract_mode,
        Scale.DISCRETE,
    ),
    "nbr_frames": Extractor(
        "The real number of frames of the video file",
        "None if frames is None else len(frames)",
        Scale.LOGARITHMIC,
    ),
    "profile": Extractor(
        "Profile of the video",
        (
            "None if height is None and width is None else "
            "best_profile(height or width, width or height)"
        ),
        Scale.DISCRETE,
    ),
    "psnr": Extractor(
        "Peak Signal to Noise Ratio (PSNR)",
        extract.extract_psnr,
        Scale.LINEAR,
    ),
    "quality": Extractor(
        "Quality level passed to the encoder",
        extract.extract_quality,
        Scale.LINEAR,
    ),
    "range": Extractor(
        "Video encoding color range, 'tv' or 'pc'",
        extract.extract_range,
        Scale.DISCRETE,
    ),
    "reference_video_stem": Extractor(
        "Input video compact stem",
        extract.extract_reference_video_stem,
        Scale.DISCRETE,
    ),
    "rms_sobel": Extractor(
        "Spacial root mean square sobel gradient complexity",
        extract.extract_rms_sobel,
        Scale.LINEAR,
    ),
    "rms_time_diff": Extractor(
        "Temporal root means square time difference complexity",
        extract.extract_rms_time_diff,
        Scale.LINEAR,
    ),
    "shape": Extractor(
        "The image shapes height x width in pixels",
        "(height, width)",
        Scale.DISCRETE,
    ),
    "ssim": Extractor(
        "Structural Similarity (SSIM)",
        extract.extract_ssim,
        Scale.LINEAR,
    ),
    "ssim_comp": Extractor(
        "Complementary of Structural Similarity (1-SSIM)",
        "None if ssim is None else 1.0 - ssim",
        Scale.LOGARITHMIC,
    ),
    "temp": Extractor(
        "Average temperature in C",
        extract.extract_temp,
        Scale.LINEAR,
    ),
    "threads": Extractor(
        "Number of threads provided as a parameter to the encoder",
        extract.extract_threads,
        Scale.LINEAR,
    ),
    "transfer": Extractor(
        "The non-linear transfer function name",
        extract.extract_transfer,
        Scale.DISCRETE,
    ),
    "vmaf": Extractor(
        "Video Multi-Method Assessment Fusion (VMAF)",
        extract.extract_vmaf,
        Scale.LINEAR,
    ),
    "video_duration": Extractor(
        "Video duration in seconds",
        extract.extract_video_duration,
        Scale.LINEAR,
    ),
    "video_hash": Extractor(
        "The hexadecimal md5 video file checksum",
        extract.extract_video_hash,
        Scale.DISCRETE,
    ),
    "video_name": Extractor(
        "Full video basename",
        extract.extract_video_name,
        Scale.DISCRETE,
    ),
    "video_size": Extractor(
        "The total video file size in bytes",
        extract.extract_video_size,
        Scale.LOGARITHMIC,
    ),
    "width": Extractor(
        "Width of images in pixels",
        extract.extract_width,  # comme dans ton code
        Scale.LINEAR,
    ),
}


ALIAS = {
    "actdur": "act_duration",
    "color_primaries": "gamut",
    "color_transfer": "transfer",
    "comp_ssim": "ssim_comp",
    "dec_cmd": "decode_cmd",
    "dec_ram": "decode_ram",
    "dec_scenario": "decode_scenario",
    "decoder_type": "decoder_family",
    "enc_cmd": "encode_cmd",
    "enc_ram": "encode_ram",
    "enc_scenario": "encode_scenario",
    "encoder_type": "encoder_family",
    "eotf": "transfer",
    "name": "video_name",
    "nb_frames": "nbr_frames",
    "preset": "effort",
    "prim": "gamut",
    "primaries": "gamut",
    "rate": "bitrate",
    "ref_stem": "reference_video_stem",
    "ref_vid_stem": "reference_video_stem",
    "ref_video_stem": "reference_video_stem",
    "reference_stem": "reference_video_stem",
    "reference_vid_stem": "reference_video_stem",
    "rev_ssim": "ssim_comp",
    "size": "video_size",
    "ssim_rev": "ssim_comp",
    "temperature": "temp",
    "trans": "transfer",
    "vid_duration": "video_duration",
    "vid_hash": "video_hash",
    "vid_md5": "video_hash",
    "vid_name": "video_name",
    "vid_size": "video_size",
    "video_md5": "video_hash",
}


def _import_extractor(code: list[str]) -> typing.Callable:
    """Import the function line_extractor."""
    code = [
        "import re",
        "",
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
    # path.unlink()
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
    >>> extract_names("[i**2 for i in foo]")
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


def get_extractor(name: str, *, safe: bool = False) -> Extractor:
    """Get the way to deserialize a raw value.

    Parameters
    ----------
    name : str
        The label name.
    safe : boolean, default=False
        If True, retrun a stupid value instead of raising KeyError.

    Returns
    -------
    extractor : Extractor
        The label, func and scale.

    """
    assert isinstance(name, str), name.__class__.__name__
    assert isinstance(safe, bool), safe.__class__.__name__
    if (extractor := ALL_EXTRACTORS.get(ALIAS.get(name, name), None)) is not None:
        return extractor
    if safe:
        return Extractor(name, name, Scale.LINEAR)
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
    <BLANKLINE>
        Causality constraint:
            * abaca -> foo
            * enc_scenario -> abaca
            * encode_cmd -> enc_scenario
            * energy -> foo
            * energy -> power
            * frames -> nbr_frames
            * hostname -> abaca
            * hostname -> enc_scenario
            * hostname -> reject
            * nbr_frames -> abaca
            * powers -> energy
            * powers -> power
            * size -> rate
            * video_duration -> rate
            * video_name -> enc_scenario
        """
        # reject wrong line
        hostname = extract.extract_hostname(raw)  # The machine name
        reject = not ("yeti" not in hostname)  # not ("yeti" not in hostname)
        if reject:
            msg = "this line must be filtered"
            raise RejectError(msg)
    <BLANKLINE>
        # extract data
        video_name = extract.extract_video_name(raw)  # Video basename
        encode_cmd = extract.extract_encode_cmd(raw)  # The ffmpeg command used for encoding
        enc_scenario = f"cmd: {encode_cmd}, video_name: {video_name}, hostname: {hostname}"  # Un...
        frames = extract.extract_frames(raw)  # The metadata of each frame
        powers = extract.extract_powers(raw)  # The interval duration and the average power in ea...
        nbr_frames = None if frames is None else len(frames)  # The real number of frames of the ...
        energy = None if powers is None else float((powers[0] * powers[1]).sum())  # Total energy...
        abaca = (hostname, nbr_frames, enc_scenario)  # alias
        foo = (abaca, energy)  # alias
        power = None if energy is None or powers is None else energy / float(powers[0].sum())  # ...
        video_duration = extract.extract_video_duration(raw)  # Video duration in seconds
        size = extract.extract_video_size(raw)  # The total video file size in bytes
        rate = None if size is None or video_duration is None else 8.0 * size / video_duration  #...
    <BLANKLINE>
        return {
            'enc_scenario': enc_scenario,
            'foo': foo,
            'power': power,
            'rate': rate,
        }
    >>>

    '''
    assert isinstance(labels, set), labels.__class__.__name__
    assert all(isinstance(lbl, str) for lbl in labels), labels
    alias = alias or {}
    assert isinstance(alias, dict), alias.__class__.__name__
    assert select is None or isinstance(select, str), select.__class__.__name__

    extractors = nx.DiGraph()

    def get_alias_extractor(alias: dict, lbl: str) -> Extractor:
        return (
            Extractor("alias", alias[lbl], get_extractor(alias[lbl], safe=True).scale)
            if lbl in alias else
            get_extractor(lbl, safe=True)
        )

    # initialise the graph with final leaves
    for label in labels:
        extractors.add_node(label, **get_alias_extractor(alias, label))
    # extractors.add_nodes_from(labels)  # adding leaves
    if select is not None:
        extractors.add_node(
            "reject", **get_extractor(f"not ({select})", safe=True),
        )

    # construct the full tree
    while nodes := [
        n for n, deg in extractors.in_degree()
        if deg == 0 and not callable(extractors.nodes[n]["func"])
    ]:
        for node in nodes:
            for root in extract_names(alias.get(node, extractors.nodes[node]["func"])):
                extractors.add_node(root, **get_alias_extractor(alias, root))
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
        *(f"        * {prev} -> {node}" for prev, node in sorted(extractors.edges)),
        '    """',
    ]
    skip: set[str] = set()  # processed nodes

    # 2) reject bad line
    if select is not None:
        code.extend([
            "    # reject wrong line",
            *_print_branch("reject", skip, extractors),
            "    if reject:",
            '        msg = "this line must be filtered"',
            "        raise RejectError(msg)",
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
        *(f"        {lbl!r}: {lbl}," for lbl in sorted(labels)),
        "    }",
    ])

    # import source code
    return (
        {n for n in extractors if callable(extractors.nodes[n]["func"])},
        (_import_extractor(code) if return_callable else code),
    )
