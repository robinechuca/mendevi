"""Provide simple tools."""

import base64
import contextlib
import functools
import hashlib
import logging
import math
import multiprocessing.pool
import numbers
import pathlib
import re
import shutil
import tempfile
import typing
from fractions import Fraction

import cutcutcodec
import tqdm
from cutcutcodec.core.io import VIDEO_SUFFIXES

from mendevi.cst.profiles import PROFILES

HASHSIZE = 16  # md5 has number of bytes
PATHLIKE = str | bytes | pathlib.Path


@functools.cache
def best_profile(height: numbers.Integral, width: numbers.Integral) -> str:
    """Return the closest profile name.

    Examples
    --------
    >>> from mendevi.utils import best_profile
    >>> best_profile(1080, 1920)
    'fhd'
    >>>

    """
    assert isinstance(height, numbers.Integral), height.__class__.__name__
    assert isinstance(width, numbers.Integral), width.__class__.__name__
    size = math.sqrt(float(height * width))
    dist_to_profile = {
        abs(math.sqrt(float(v["resolution"][0]*v["resolution"][1])) - size): p
        for p, v in PROFILES.items()
    }
    return dist_to_profile[min(dist_to_profile)]


def compute_video_hash(
    videos: PATHLIKE | typing.Iterable[PATHLIKE], *, fast: bool=True,
) -> bytes | dict[pathlib.Path, bytes]:
    r"""Compute the checksum of the video.

    For :math:`n` hash of :math:`b` bits, the proba of the colision :math:`C` is
    :math:`p(C) = 1 - \left(\frac{2^k-1}{2^k}\right)^{\frac{n(n-1)}{2}}`.

    The md5 hash uses :math:`b = 128` bits. If we add one video per second durring 10 years,
    the proba of colision is about :math:`p(C) \approx 1.46*10^{-22}`.

    That's why the md5 hash is used to identify the video files.

    Parameters
    ----------
    videos : pathlike or list[pathlike]
        The single or set of video you want to compute the signature.
    fast : boolean, default=True
        If the hash appears in the file name, it is returned immediately.
        If False, the actual checksum is systematically recalculated.

    Returns
    -------
    signatures
        The md5 checksum of the video file. In the case of a multiple file,
        a dictionary containing the file and the hash is returned rather a single hash.
        If the file does not exists, return None.

    """
    assert isinstance(fast, bool), fast.__class__.__name__

    def _hash(video_fast: tuple[PATHLIKE, bool]) -> pathlib.Path:
        video, fast = video_fast
        video = pathlib.Path(video)
        # [2-7a-z]{26} for mendevi > 1.2.2
        if fast and (match := re.search(r"[0-9a-f]{32}|[2-7a-z]{26}", video.stem)):
            return video, signature_to_hash(match.group())
        if not (video := video.expanduser()).is_file():
            return video, None
        with video.open("rb") as raw:
            return video, hashlib.file_digest(raw, "md5").digest()

    if isinstance(videos, list | tuple | set | frozenset):
        with multiprocessing.pool.ThreadPool() as pool:
            return dict(tqdm.tqdm(
                pool.imap_unordered(_hash, ((v, fast) for v in videos)),
                desc="compute videos checksum",
                dynamic_ncols=True,
                leave=False,
                smoothing=1e-6,
                total=len(videos),
                unit="video",
            ))
    return _hash((videos, fast))[1]


@contextlib.contextmanager
def cp_shm(file: pathlib.Path, threshold: float) -> pathlib.Path:
    """Copy the file into /dev/shm is there is enougth free space, otherwise in /tmp."""
    assert isinstance(file, pathlib.Path), file.__class__.__name__
    assert file.exists(), file
    shm = pathlib.Path("/dev/shm")
    tmp = pathlib.Path(tempfile.gettempdir())
    file_copy = None
    if (
        file.parts[:len(shm.parts)] != shm.parts  # avoid copy to the same device
        and shutil.disk_usage(shm).free > threshold * file.stat().st_size
    ):
        file_copy = shm / file.name
        shutil.copy(file, file_copy)
    elif file.parts[:len(tmp.parts)] != tmp.parts:
        file_copy = tmp / file.name
        shutil.copy(file, file_copy)
    try:
        yield file_copy or file
    finally:
        if file_copy is not None:
            file_copy.unlink()


@functools.cache
def get_pix_fmt(*args: tuple) -> str:
    """Alias to cutcutcodec func."""
    return cutcutcodec.get_pix_fmt(*args)


def get_project_root() -> pathlib.Path:
    """Return the absolute project root folder.

    Examples
    --------
    >>> from mendevi.utils import get_project_root
    >>> root = get_project_root()
    >>> root.is_dir()
    True
    >>> root.name
    'mendevi'
    >>> sorted(p.name for p in root.iterdir())  # doctest: +ELLIPSIS
    ['__init__.py', '__main__.py', ...]
    >>>

    """
    return pathlib.Path(__file__).resolve().parent


@functools.cache
def get_rate_video(*args: tuple) -> Fraction:
    """Alias to cutcutcodec func."""
    return cutcutcodec.get_rate_video(*args)


@functools.cache
def get_resolution(*args: tuple) -> tuple[int, int]:
    """Alias to cutcutcodec func."""
    return cutcutcodec.get_resolution(*args)


def hash_to_signature(checksum: bytes) -> str:
    r"""Convert the md5 binary hash value into an urlsafe string.

    Bijection of :py:func:`signature_to_hash`.

    Parameters
    ----------
    checksum : bytes
        The 128 bit binary hash value.

    Returns
    -------
    signature : str
        The 26 ascii [2-7a-z] symbols string of the converted checksum.

    Examples
    --------
    >>> from mendevi.utils import hash_to_signature
    >>> hash_to_signature(b"\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~")
    'd41d8cd98f00b204e9800998ecf8427e'
    >>>

    """
    assert isinstance(checksum, bytes), checksum.__class__.__name__
    assert len(checksum) == HASHSIZE, len(checksum)
    return checksum.hex()


def signature_to_hash(signature: str) -> bytes:
    r"""Convert the string signature into the md5 checksum.

    Bijection of :py:func:`hash_to_signature`.

    Parameters
    ----------
    signature : str
        The 26 ascii [2-7a-z] symbols string of the converted checksum.

    Returns
    -------
    checksum : bytes
        The 128 bit binary hash value.

    Examples
    --------
    >>> from mendevi.utils import signature_to_hash
    >>> signature_to_hash("d41d8cd98f00b204e9800998ecf8427e")
    b'\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~'
    >>> signature_to_hash("2qoyzwmpaczaj2mabgmoz6ccpy")  # mendevi < 1.2.2
    b'\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~'
    >>>

    """
    assert isinstance(signature, str), signature.__class__.__name__
    try:  # version >= 1.2.2
        assert re.fullmatch(r"[0-9a-f]{32}", signature), signature
    except AssertionError:  # retrocompatibility version < 1.2.2
        assert re.fullmatch(r"[2-7a-z]{26}", signature), signature
        return base64.b32decode(f"{signature.upper()}======".encode())
    else:
        return bytes.fromhex(signature)


def unfold_video_files(
    paths: typing.Iterable[PATHLIKE],
) -> typing.Iterable[pathlib.Path]:
    """Explore recursively the folders to find the video path.

    Parameters
    ----------
    paths : list[pathlike]
        All the folders, files, glob or recursive glob expression.

    Yields
    ------
    filename : pathlib.Path
        The path of the video.

    """
    assert hasattr(paths, "__iter__"), paths.__class__.__name__
    for path_general in paths:
        path = pathlib.Path(path_general).expanduser()
        if path.is_file():
            yield path
        elif path.is_dir():
            for root, _, files in path.walk():
                for file_name in files:
                    file = root / file_name
                    if file.suffix.lower() in VIDEO_SUFFIXES:
                        yield file
        elif "*" in path.name and path.parent.is_dir():
            yield from unfold_video_files(path.parent.glob(path.name))
        elif "**" in (parts := path.parts):
            idx = parts.index("**")
            yield from unfold_video_files(
                pathlib.Path(*parts[:idx]).glob(pathlib.Path(*parts[idx:])),
            )
        else:
            logging.getLogger(__name__).warning("the path %s is not correct", path)
