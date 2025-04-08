#!/usr/bin/env python3

"""Merges multiple json contents."""

import json
import pathlib
import shutil

import filelock


def merge_data(data_ref: object, data_new: object) -> object:
    """Merge the new data into the ref data.

    Parameters
    ----------
    data_ref : object
        The jsonisable object that will be extended by data_new.
        It can be modified inplace.
    data_new : object
        The jsonisable object to be added to the reference content.

    Returns
    -------
    data_merge : object
        Merging data_ref and data_new. Can be a data_ref reference.

    Examples
    --------
    >>> from mendevi.merge import merge_data
    >>> merge_data("text 1", "text 2")
    ['text 1', 'text 2']
    >>> merge_data("text 1", "text 2")
    >>> merge_data(["text 1"], "text 2")
    ['text 1', 'text 2']
    >>> merge_data({"key1": "d1_1", "key2": "d1_2"}, {"key2": "d2_2", "key3": "d2_3"})
    {'key1': 'd1_1', 'key2': ['d1_2', 'd2_2'], 'key3': 'd2_3'}
    >>>
    """
    if isinstance(data_ref, list):
        data_ref.append(data_new)
        return data_ref
    if isinstance(data_ref, dict) and isinstance(data_new, dict):
        for new_key, new_value in data_new.items():
            if new_key not in data_ref:
                data_ref[new_key] = new_value
            else:
                data_ref[new_key] = merge_data(data_ref[new_key], new_value)
        return data_ref
    return [data_ref, data_new]  # default case


def merge_file(file: pathlib.Path | str | bytes, data_new: object):
    """Add a content into a json file.

    Parameters
    ----------
    file : pathlike
        A json file to be updated with new content.
    data_new : object
        The jsonisable object to be added to the json file.

    Notes
    -----
    This function is locked so that it can be called from different processes.
    """
    file = pathlib.Path(file).expanduser()

    with filelock.FileLock(file.with_suffix(".lock")):
        try:
            with open(file, "r", encoding="utf-8") as raw:
                data_ref = json.load(raw)
        except FileNotFoundError:
            data_ref = {}
        data_ref = merge_data(data_ref, data_new)
        import pprint
        pprint.pprint(data_ref)
        with open(file.with_suffix(".tmp"), "w", encoding="utf-8") as raw:
            json.dump(data_ref, raw, sort_keys=True, indent=4)
        shutil.move(file.with_suffix(".tmp"), file)
