"""Decompress a file."""

import logging
import lzma
import pathlib
import re
import subprocess

import tqdm
from context_verbose import Printer


def _get_size(compressed_file: pathlib.Path) -> int:
    """Try to get the decompressed size with 'xz'."""
    # this method should be improved
    try:
        out = subprocess.run(
            ["xz", "--robot", "--list", str(compressed_file)], check=True, capture_output=True,
        )
    except FileNotFoundError as err:
        logging.getLogger(__name__).warning("please install xz %s", err)
    sizes = re.findall(br"\d+", out.stdout)
    return max(map(int, sizes), default=0)


def decompress(compressed_file: pathlib.Path) -> pathlib.Path:
    """Decompress a *.xz file in the same folder."""
    assert isinstance(compressed_file, pathlib.Path), compressed_file.__class__.__name__
    assert compressed_file.suffix == ".xz", compressed_file
    decompressed_file = compressed_file.parent / compressed_file.stem

    # shortcut
    size = None
    if decompressed_file.exists():
        size = _get_size(compressed_file)
        if decompressed_file.stat().st_size == size:
            return decompressed_file

    # decompress
    with Printer(f"Decompress {compressed_file.name!r}...", color="green") as prt:
        if size is None:
            size = _get_size(compressed_file)

        with (
            tqdm.tqdm(
                dynamic_ncols=True,
                leave=True,
                smoothing=1e-6,
                total=round(size*1e-6, 1),
                unit="Mo",
            ) as load,
            lzma.open(compressed_file, "r") as src,
            decompressed_file.open("wb") as dst,
        ):

            while data := src.read(1_000_000):
                dst.write(data)
                load.total = max(load.total, load.n + len(data)*1e-6)
                load.update(len(data)*1e-6)
            prt.print_time()

    return decompressed_file
