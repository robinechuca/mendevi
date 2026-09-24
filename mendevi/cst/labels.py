# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""All the available fields."""

from mendevi.database.meta import ALIAS, ALL_EXTRACTORS

LABELS = sorted(set(ALL_EXTRACTORS) | set(ALIAS))
LABELS.extend([f"log_{lbl}" for lbl in LABELS])  # [] required, generator leads to infinite loop
