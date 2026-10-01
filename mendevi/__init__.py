# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Mesures d'Encodage et Décodage Vidéo."""

from .measures import Activity
from .measures.context import full_context as context

__all__ = ["Activity", "context"]
__author__ = "Robin RICHARD (robinechuca)"
__version__ = "1.4.0"  # pep 440
