# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Pereform several tests on the Activity class."""

import time

import pytest

from mendevi.measures import RAPL, Activity


def test_rapl_no_fail() -> None:
    """Ensure it works even without sudo."""
    with RAPL(no_fail=True) as res:
        assert res is None or isinstance(res, dict)


def test_unique_slice() -> None:
    """Ensure we can not call .start_slice with the same label twice."""
    with Activity() as act:
        act.start_slice("label")
        with pytest.raises(KeyError, match=r"the method start_slice has already been called.*"):
            act.start_slice("label")


def test_unique_stop() -> None:
    """Ensure we can not call stop_slice twice or when no slice in process."""
    with Activity() as act, pytest.raises(RuntimeError, match="no slice capture in process"):
        act.stop_slice()
    with Activity() as act:
        act.start_slice("label")
        act.stop_slice()
        with pytest.raises(RuntimeError, match="no slice capture in process"):
            act.stop_slice()


def test_structure() -> None:
    """Retrocompatibility test."""
    with Activity() as act:
        pass
    res = act.get_full()
    assert isinstance(res, dict)
    assert {
        "duration", "ps_core", "ps_core_avg", "ps_ram", "ps_ram_avg", "ps_ts", "start",
    }.issubset(res.keys())
    assert res == act.get_full()


def test_slices_duration() -> None:
    """Ensure sublices fit in the full capture activity."""
    wait = 0.1
    with Activity() as act:
        act.start_slice("lbl1")
        time.sleep(wait)
        act.start_slice("lbl2")
        time.sleep(wait)
    slices, full = act.get_slices(), act.get_full()
    cum_duration = sum(s["duration"] for s in slices.values())
    assert full["duration"] >= cum_duration  # sublices fit in the full capture activity
    assert round(full["duration"], 1) == round(cum_duration, 1)  # total close of sum of slices
    assert round(slices["lbl1"]["duration"], 1) == wait
    assert round(slices["lbl2"]["duration"], 1) == wait


def test_slices_numbers() -> None:
    """Ensure slices are all restitued with correct label."""
    loops = 1024
    with Activity() as act:
        for i in range(loops):
            act.start_slice(i)
    slices = act.get_slices()
    assert set(slices) == set(range(loops))


def test_slices_fields() -> None:
    """Test the returns slices fields."""
    with Activity() as act:
        act.start_slice("lbl")
    slices = act.get_slices()
    assert isinstance(slices, dict)
    assert isinstance(slices["lbl"], dict)
    assert {"start", "duration", "ps_dt", "ps_core"}.issubset(slices["lbl"].keys())
