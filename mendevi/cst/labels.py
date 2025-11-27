#!/usr/bin/env python3

"""All the available fields."""

from mendevi.database.meta import ALL_EXTRACTORS, ALIAS


LABELS = sorted(set(ALL_EXTRACTORS) | set(ALIAS))
