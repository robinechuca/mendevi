# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""All the available decoders."""

from mendevi.decode import DECODERS_CAT

DECODERS = {dec[1] for decs in DECODERS_CAT.values() for dec in decs}
