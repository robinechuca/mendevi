# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""All the available models."""

import functools
import importlib
import inspect
import sys

from mendevi.models.base import Model
from mendevi.utils import get_project_root


def _yield_all_models() -> Model:
    """Discover the Model instances in mendevi/models/*.py."""
    for path in (get_project_root() / "models").glob("*.py"):
        if path.stem in {"__init__", "base"}:  # skip root module
            continue
        modulename = f"mendevi.models.{path.stem}"
        spec = importlib.util.spec_from_file_location(modulename, path)
        modulevar = importlib.util.module_from_spec(spec)
        sys.modules[modulename] = modulevar  # to avoid pickle error: it's not the same object...
        spec.loader.exec_module(modulevar)
        for name in dir(modulevar):
            var = modulevar.__dict__[name]
            if inspect.isclass(var) and issubclass(var, Model) and var is not Model:
                yield name, var


@functools.cache
def import_all_models() -> dict[str, Model]:
    """Import all the class in mendevi/models/*.py that inherit from Model.

    Examples
    --------
    >>> from pprint import pprint
    >>> from mendevi.cst.model import import_all_models
    >>> pprint(import_all_models())
    {'DNN': <class 'mendevi.models.dnn.DNN'>,
     'DecodeEnergyNN': <class 'mendevi.models.dnn.DecodeEnergyNN'>,
     'EncodeEnergyNN': <class 'mendevi.models.dnn.EncodeEnergyNN'>,
     'EncodeLinear': <class 'mendevi.models.lr.EncodeLinear'>,
     'GPR': <class 'mendevi.models.gpr.GPR'>,
     'KernelMultiHead': <class 'mendevi.models.dnn.KernelMultiHead'>,
     'LR': <class 'mendevi.models.lr.LR'>,
     'NearestL2': <class 'mendevi.models.interp.NearestL2'>,
     'PowerCores': <class 'mendevi.models.power_cores.PowerCores'>,
     'QBP': <class 'mendevi.models.qbp.QBP'>,
     'QualityNN': <class 'mendevi.models.dnn.QualityNN'>}
    >>>

    """
    return dict(_yield_all_models())
