#!/usr/bin/env python3

"""Unify all the models with a common sctucture."""

import abc
import logging
import pathlib
import sqlite3
import typing

import numpy as np
import torch

from mendevi.cst.labels import LABELS
from mendevi.database.create import is_sqlite
from mendevi.database.extract import SqlLinker
from mendevi.database.meta import get_extractor


class Model(abc.ABC):
    """Common structure to all models.

    Attributes
    ----------
    cite : str
        The latex bibtext model citation.
    parameters : torch.Tensor | None
        The trainable parameters of the model (read and write).
    input_labels : list[str]
        The name of all input parameters (readonly).
    output_labels : list[str]
        The name of all output parameters (readonly).
    """

    def __init__(self, title: typing.Optional[str] = None, **kwargs):
        """Initialise the model.

        Parameters
        ----------
        title : str, optional
            The model title.
        sources : str
            All sources for the model, the conference paper, the authors, etc.
        input_labels : list[str]
            The name of all input parameters.
            The possibles values are :py:cst:`mendevi.plot.axis.Name`.
        output_labels : list[str]
            The name of all output parameters.
            The possibles values are :py:cst:`mendevi.plot.axis.Name`.
        parameters : torch.Tensor, optional
            The learnable parameters for regressive models.
        """
        # check input_labels
        input_labels = kwargs.get("input_labels", [])
        assert hasattr(input_labels, "__iter__"), input_labels.__class__.__name__
        input_labels = list(input_labels)
        assert input_labels, "input must be not empty"
        assert all(isinstance(lab, str) and lab in LABELS for lab in input_labels), input_labels
        self._input_labels = input_labels

        # check output_labels
        output_labels = kwargs.get("output_labels", [])
        assert hasattr(output_labels, "__iter__"), output_labels.__class__.__name__
        output_labels = list(output_labels)
        assert output_labels, "output must be not empty"
        assert all(isinstance(lab, str) and lab in LABELS for lab in output_labels), output_labels
        self._output_labels = output_labels

        # check parameters
        if (parameters := kwargs.get("parameters", None)) is not None:
            parameters = torch.asarray(parameters)
        self._parameters = None

        # check title
        if title is None:
            title = (
                f"{'regressive ' if self._parameters is not None else ''}model "
                f"to predict {', '.join(sorted(self._output))} "
                f"from {', '.join(sorted(self._input))}"
            )
        else:
            assert isinstance(title, str), title.__class__.__name__
        self._title = title

        # check authors
        sources = kwargs.get("sources", "")
        assert isinstance(sources, str), sources.__class__.__name__
        self._sources = sources

    def _fit(self, values: dict[str]):
        """Perform regression on parameters ``self.parameters``."""
        raise NotImplementedError

    @abc.abstractmethod
    def _predict(self, values: dict[str]) -> dict[str]:
        """Implement the heart of the model."""
        raise NotImplementedError

    @property
    def cite(self) -> str:
        """Return the bibtex citation."""
        raise NotImplementedError

    def fit(self, database: pathlib.Path | str, query: typing.Optional[str] = None) -> typing.Self:
        """Fit the trainable hyper parameters of the models.

        Parameters
        ----------
        database : pathlike
            The training database.
        query : str, optional
            If provided, use this sql query to perform the request,
            otherwise (default) attemps to guess the query.

        Return
        ------
        self
            A reference to the inplace fitted model.
        """
        # verification
        if self._parameters is None:
            raise RuntimeError("This model is not trainable.")
        database = pathlib.Path(database).expanduser()
        assert is_sqlite(database), f"{database} is not a valid SQL database"

        # get sql query
        funcs = {n: get_extractor(n).func for n in self._input_labels}
        if query is None:
            select = {s for f in funcs.values() for s in f.select}
            if len(queries := SqlLinker(*select).sql) == 0:
                raise RuntimeError("fail to create the SQL query, please provide it yourself")
            if len(queries) > 1:
                logging.warning("several request founded %s, please provide it yourself", queries)
            query = queries.pop(0)
        else:
            assert isinstance(query, str), query.__class__.__name__

        # perform sql request
        values = {label: [] for label in funcs}
        with sqlite3.connect(database) as conn:
            conn.row_factory = sqlite3.Row
            for raw in conn.execute(query):
                raw = dict(raw)
                for label, func in funcs.items():
                    values[label].eppend(func(raw))

        # fit the model
        self._fit(values)
        return self

    @property
    def input_labels(self) -> list[str]:
        """Return the name of all input parameters."""
        return self._input_labels.copy()

    @property
    def output_labels(self) -> list[str]:
        """Return the name of all output parameters."""
        return self._output_labels.copy()

    @property
    def parameters(self) -> torch.Tensor or None:
        """Return the trainable parameters of the model."""
        return self._parameters

    @parameters.setter
    def parameters(self, new_params: torch.Tensor):
        """Update the parameters."""
        new_params = torch.asarray(new_params)
        if self._parameters is not None:
            assert self._parameters.shape == new_params.shape
        self._parameters = new_params

    def predict(self, *input_args, **input_kwargs) -> dict[str]:
        """Perform the prediction(s) of this model.

        Parameters
        ----------
        *input_args, **input_kwargs
            The parameters values, with the keys defined during initialisation.

        Returns
        -------
        prediction : dict[str]
            Associate each ouput variable with the prediction.
        """
        # check args
        values: dict[str] = {}
        for i, arg in enumerate(input_args):
            if i == len(self._input_labels):
                raise ValueError(
                    f"only {len(self._input)} arguments expeted {self._input_labels}, "
                    f"{input_args} given"
                )
            values[self._input_labels[i]] = arg
        for name, arg in input_kwargs.items():
            if name in values:
                raise ValueError(f"argument {name} given twice")
            if name not in self._input:
                raise ValueError(f"only {self._input_labels} arguments excpected, not {name}")
            values[name] = arg

        # cast args
        for name, arg in values.copy().items():
            match arg:
                case float():
                    values[name] = torch.asarray(arg, dtype=torch.float32)
                case np.ndarray():
                    values[name] = torch.from_numpy(arg)
                case list():
                    if all(isinstance(item, float) for item in arg):
                        values[name] = torch.asarray(arg, dtype=torch.float32)

        # predict
        prediction = self._predict(values)

        # chack output
        assert isinstance(prediction, dict), prediction.__class__.__name__
        assert prediction.key() == set(self._output), \
            f"_predict must return {self._output}, not {sorted(prediction)}"

        return prediction
