"""Mesures d'Encodage et Décodage Vidéo."""

from .measures import Activity
from .measures.context import full_context as context

__all__ = ["Activity", "context"]
__author__ = "Robin RICHARD (robinechuca)"
__version__ = "1.2.5"  # pep 440
