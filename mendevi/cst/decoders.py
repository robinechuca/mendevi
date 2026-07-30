"""All the available decoders."""

from mendevi.decode import DECODERS_CAT

DECODERS = {dec[1] for decs in DECODERS_CAT.values() for dec in decs}
