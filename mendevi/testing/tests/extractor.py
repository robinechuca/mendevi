# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Test special issues of merge_extractors."""

import pytest

from mendevi.database.meta import merge_extractors


def test_alias_cycle() -> None:
    """Ensure it raises ValueError if the alias are cycling."""
    with pytest.raises(ValueError, match=r".*graph has cycles.*"):
        merge_extractors({"foo"}, alias={"foo": "toto", "toto": "foo"})


def test_not_defined() -> None:
    """Ensure it raises ValueError if a variable is not defined."""
    with pytest.raises(ValueError, match=r".*graph has cycles.*"):
        merge_extractors({"foo"})
