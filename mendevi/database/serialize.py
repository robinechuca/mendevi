#!/usr/bin/env python3

"""Serialize the sql binary data."""

import functools
import struct

import numpy as np


VECT_DTYPE = np.float32


def skip_none(func: callable) -> callable:
    """Decorator to skip the process of None input."""
    @functools.wraps(func)
    def decorated_func(arg: object | None) -> object | None:
        return None if arg is None else func(arg)
    return decorated_func


@skip_none
def list_to_binary(vect: list[float]) -> bytes:
    r"""Serialize a float vector into binary data.

    Bijection of :py:func:`binary_to_list`.

    Parameters
    ----------
    vect : arralike
        The list of floats

    Returns
    -------
    data : bytes
        The serialized float32 list.

    Examples
    --------
    >>> from mendevi.database.serialize import list_to_binary
    >>> list_to_binary([0.0, -1.0, 0.123456789])
    b'\x00\x00\x00\x00\x00\x00\x80\xbf\xea\xd6\xfc='
    >>>
    """
    vect = np.asarray(vect, dtype=VECT_DTYPE)
    assert vect.ndim == 1, vect.shape
    return vect.tobytes("C")


@skip_none
def binary_to_list(data: bytes) -> np.ndarray[VECT_DTYPE]:
    r"""Deserialize a binary data into a float vector.

    Bijection of :py:func:`list_to_binary`.

    Parameters
    ----------
    data : bytes
        The serialized float 32 list.

    Returns
    -------
    vect : np.ndarray
        The list of floats

    Examples
    --------
    >>> from mendevi.database.serialize import binary_to_list
    >>> binary_to_list(b'\x00\x00\x00\x00\x00\x00\x80\xbf\xea\xd6\xfc=')
    array([ 0.        , -1.        ,  0.12345679], dtype=float32)
    >>>
    """
    assert isinstance(data, bytes), data.__class__.__name__
    assert len(data) % np.dtype(VECT_DTYPE).itemsize == 0, len(data)
    return np.frombuffer(data, dtype=VECT_DTYPE, count=len(data)//np.dtype(VECT_DTYPE).itemsize)


@skip_none
def tensor_to_binary(tensor: list[list[float]]) -> bytes:
    r"""Serialize a 2d array into binary data.

    Bijection os :py:func:`binary_to_tensor`.

    Parameters
    ----------
    tensor : arraylike
        The list of list of float

    Returns
    -------
    data : bytes
        The serialized float32 tensor.

    Examples
    --------
    >>> from mendevi.database.serialize import tensor_to_binary
    >>> tensor_to_binary([[1.1, 2.2], [3.3, 4.4], [5.5, 6.6]])
    b'\x02\x00\x00\x00\xcd\xcc\x8c?\xcd\xcc\x0c@33S@\xcd\xcc\x8c@\x00\x00\xb0@33\xd3@'
    >>>
    """
    tensor = np.asarray(tensor, dtype=VECT_DTYPE)
    assert tensor.ndim == 2, tensor.shape
    return struct.pack("I", tensor.shape[1]) + tensor.tobytes("C")


@skip_none
def binary_to_tensor(data: bytes) -> np.ndarray[VECT_DTYPE, VECT_DTYPE]:
    r"""Serialize a 2d array into binary data.

    Bijection os :py:func:`binary_to_tensor`.

    Parameters
    ----------
    data : bytes
        The serialized float32 tensor.

    Returns
    -------
    tensor : np.ndarray
        The list of list of float

    Examples
    --------
    >>> from mendevi.database.serialize import binary_to_tensor
    >>> data = b'\x02\x00\x00\x00\xcd\xcc\x8c?\xcd\xcc\x0c@33S@\xcd\xcc\x8c@\x00\x00\xb0@33\xd3@'
    >>> binary_to_tensor(data)
    array([[1.1, 2.2],
           [3.3, 4.4],
           [5.5, 6.6]], dtype=float32)
    >>>
    """
    assert isinstance(data, bytes), data.__class__.__name__
    size, data = data[:4], data[4:]
    return np.frombuffer(data, dtype=VECT_DTYPE).reshape(-1, struct.unpack("I", size)[0])
