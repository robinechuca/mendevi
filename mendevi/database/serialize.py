#!/usr/bin/env python3

"""Serialize the sql binary data."""

import numpy as np

VECT_DTYPE = np.float32


def list_to_binary(vect: list) -> bytes:
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
    return np.asarray(vect, dtype=VECT_DTYPE).tobytes("C")


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
