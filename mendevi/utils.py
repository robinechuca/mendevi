#!/usr/bin/env python3

"""Provide simple tools."""

import base64
import functools
import hashlib
import logging
import multiprocessing.pool
import numbers
import pathlib
import platform
import queue
import re
import threading
import time
import typing

from cutcutcodec.core.io import VIDEO_SUFFIXES
import cutcutcodec
import tqdm

from mendevi.g5kpower import g5kpower
from mendevi.psutil import Usage
from mendevi.rapl import RAPL

PATHLIKE = str | bytes | pathlib.Path


class Activity(threading.Thread):
    """Measure the computer activity of a section.

    Examples
    --------
    >>> import pprint, time
    >>> from mendevi.utils import Activity
    >>> with Activity() as activity:
    ...     time.sleep(1)
    ...
    >>> pprint.pprint(activity)
    >>>
    """

    def __init__(self, sleep: numbers.Real=50e-3):
        """Initalize the perf context.

        Parameters
        ----------
        sleep : float, default=50e-3
            The time interval between 2 measures (in s).
        """
        assert isinstance(sleep, numbers.Real), sleep.__class__.__name__
        assert sleep > 0, sleep

        super().__init__(daemon=True)

        self._rapl_catcher = RAPL(sleep=sleep, no_fail=True)
        self._usage_catcher = Usage(sleep=sleep)
        self._exit_queue = queue.Queue()
        self.sleep = float(sleep)
        self.res: dict = {}

    def run(self):
        """Perform the measures."""
        self.res["start"] = time.time()
        with self._rapl_catcher as rapl, self._usage_catcher as usage:
            self._exit_queue.get()  # wait
        self.res |= {
            "ps_core": usage["cpu"],
            "ps_cores": usage["cpus"],
            "ps_dt": usage["dt"],
            "ps_ram": usage["ram"],
        }
        if rapl is not None:
            self.res |= {
                "rapl_dt": rapl["dt"],
                "rapl_energy": rapl["energy"],
                "rapl_power": rapl["power"],
                "rapl_powers": rapl["powers"],
            }

    def __enter__(self) -> dict:
        r"""Start to measure.

        Returns
        -------
        activity: dict[str]
            * duration: float, the real measure duration.
            * ps_core: float, the mean cummulated usage of all the logical cpus.
            * ps_cores: list[list[float]], tensor of detailed usage of each logical core in %.
            * ps_dt: list[float], the duration of each interval (in s).
            * ps_ram: list[int], list of the sampled ram usage in bytes in each point.
            * rapl_dt: list[float], the duration of each interval (in s).
            * rapl_energy: float, the total energy consumption (in J).
            * rapl_power: float, the average power, energy divided by the duration (in w).
            * rapl_powers: list[float], the average power in watt in each interval.
            * start: float, absolute timestamp.
            * wattmeter_dt: list[float],  the duration of each interval (in s).
            * wattmeter_energy: float, the total energy consumption (in J).
            * wattmeter_power: float, the average power, energy divided by the duration (in w).
            * wattmeter_powers: list[float], the sampled power in watt in each point.

        Notes
        -----
        The returned dictionary is update inplace when we exit the code bloc.
        Only the successfull field are created.
        """
        self.start()
        return self.res

    def __exit__(self, *_):
        """Stop the measure and update the dictionary returnd by __enter__."""
        # stop
        self.res["duration"] = time.time() - self.res["start"]
        self._exit_queue.put(None)
        self.join()
        # request wattmeter power
        try:
            wattmeter = g5kpower(platform.node(), self.res["start"], self.res["duration"])
        except ValueError:
            wattmeter = None
        else:
            self.res |= {
                "wattmeter_dt": wattmeter["dt"],
                "wattmeter_energy": wattmeter["energy"],
                "wattmeter_power": wattmeter["power"],
                "wattmeter_powers": wattmeter["powers"],
            }


def compute_video_hash(
    videos: PATHLIKE | typing.Iterable[PATHLIKE]
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

    Returns
    -------
    signatures
        The md5 checksum of the video file. In the case of a multiple file,
        a dictionary containing the file and the hash is returned rather a single hash.
        If the file does not exists, return None.
    """
    def _hash(video: PATHLIKE) -> pathlib.Path:
        video = pathlib.Path(video)
        if match := re.search(r"[2-7a-z]{26}", video.stem):
            return video, signature_to_hash(match.group())
        if not (video := video.expanduser()).is_file():
            return video, None
        with open(video, "rb") as raw:
            return video, hashlib.file_digest(raw, "md5").digest()

    if isinstance(videos, list | tuple | set | frozenset):
        with multiprocessing.pool.ThreadPool() as pool:
            return dict(tqdm.tqdm(
                pool.imap_unordered(_hash, videos),
                desc="compute videos checksum",
                dynamic_ncols=True,
                leave=False,
                smoothing=1e-6,
                total=len(videos),
                unit="video",
            ))
    return _hash(videos)[1]


@functools.cache
def get_pix_fmt(*args):
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
def get_rate_video(*args):
    """Alias to cutcutcodec func."""
    return cutcutcodec.get_rate_video(*args)


@functools.cache
def get_resolution(*args):
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
    '2qoyzwmpaczaj2mabgmoz6ccpy'
    >>>
    """
    assert isinstance(checksum, bytes), checksum.__class__.__name__
    assert len(checksum) == 16, len(checksum)
    return base64.b32encode(checksum)[:26].decode().lower()


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
    >>> signature_to_hash("2qoyzwmpaczaj2mabgmoz6ccpy")
    b'\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~'
    >>>
    """
    assert isinstance(signature, str), signature.__class__.__name__
    assert re.fullmatch(r"[2-7a-z]{26}", signature), signature
    return base64.b32decode(f"{signature.upper()}======".encode())


def unfold_video_files(
    paths: typing.Iterable[PATHLIKE]
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
    for path in paths:
        path = pathlib.Path(path).expanduser()
        if path.is_file():
            yield path
        elif path.is_dir():
            for root, _, files in path.walk():
                for file in files:
                    file = root / file
                    if file.suffix.lower() in VIDEO_SUFFIXES:
                        yield file
        elif "*" in path.name and path.parent.is_dir():
            yield from unfold_video_files(path.parent.glob(path.name))
        elif "**" in (parts := path.parts):
            idx = parts.index("**")
            yield from unfold_video_files(
                pathlib.Path(*parts[:idx]).glob(pathlib.Path(*parts[idx:]))
            )
        else:
            logging.warning("the path %s is not correct", path)
