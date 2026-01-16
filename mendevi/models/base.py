"""Unify all the models with a common sctucture."""

import abc
import logging
import pathlib
import sqlite3
import typing

import numpy as np
import torch
from context_verbose import Printer

from mendevi.cst.labels import LABELS
from mendevi.database.create import is_sqlite
from mendevi.database.extract import SqlLinker
from mendevi.database.meta import get_extractor, merge_extractors
from mendevi.download.decapsulation import retrive_file


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

    def __init__(self, title: str | None = None, **kwargs: dict) -> None:
        """Initialise the model.

        Parameters
        ----------
        title : str, optional
            The model title.
        **kwargs : dict
            Includes the following fields.
        sources : str
            All sources for the model, the conference paper, the authors, etc.
        input_labels : list[str]
            The name of all input parameters.
            The possibles values are `mendevi.plot.axis.Name`.
        output_labels : list[str]
            The name of all output parameters.
            The possibles values are `mendevi.plot.axis.Name`.
        parameters : object, optional
            The learnable parameters for regressive models.

        """
        assert set(kwargs).issubset({"sources", "input_labels", "output_labels", "parameters"})
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
        self._parameters = kwargs.get("parameters")

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

    def _fit(self, values: dict[str]) -> typing.Never:
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

    def fit(
        self,
        database: pathlib.Path | str,
        select: str | None = None,
        query: str | None = None,
    ) -> typing.Self:
        """Fit the trainable hyper parameters of the models.

        Parameters
        ----------
        database : pathlike
            The training database.
        select : str, optional
            The python expression to keep the line, like ``mendevi plot --filter``.
        query : str, optional
            If provided, use this sql query to perform the request,
            otherwise (default) attemps to guess the query.

        Return
        ------
        self
            A reference to the inplace fitted model.

        """
        with Printer(f"Fit {self._title!r}...", color="pink") as prt:
            # verification
            database = retrive_file(database)
            assert is_sqlite(database), f"{database} is not a valid SQL database"

            # get sql query
            prt.print("get SQL query")
            atom_names, line_extractor = merge_extractors(
                set(self._input_labels) | set(self._output_labels),
                select=select,
                return_callable=True,
            )
            if query is None:
                select = {s for lbl in atom_names for s in get_extractor(lbl).func.select}
                if len(queries := SqlLinker(*select).sql) == 0:
                    msg = "fail to create the SQL query, please provide it yourself"
                    raise RuntimeError(msg)
                if len(queries) > 1:
                    logging.getLogger(__name__).warning(
                        "several request founded %s, please select it yourself", queries,
                    )
                query = queries.pop(0)
            else:
                assert isinstance(query, str), query.__class__.__name__

            # perform sql request
            prt.print("perform SQL query")
            values = {label: [] for label in set(self._input_labels) | set(self._output_labels)}
            with sqlite3.connect(database) as conn:
                conn.row_factory = sqlite3.Row
                for raw in conn.execute(query):
                    for label, value in line_extractor(dict(raw)).items():
                        values[label].append(value)

            # fit the model
            prt.print("fit the model")
            self._fit(values)

            prt.print_time()
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
    def parameters(self, new_params: torch.Tensor) -> None:
        """Update the parameters."""
        if self._parameters is not None and new_params.__class__ != self._parameters.__class__:
            logging.getLogger(__name__).warning("chage the type of parameters")
        self._parameters = new_params

    def predict(self, *input_args: tuple, **input_kwargs: dict) -> dict[str]:
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
        with Printer(f"Predict {self._title!r}...", color="pink") as prt:
            # check args
            prt.print("check args")
            values: dict[str] = {}
            for i, arg in enumerate(input_args):
                assert i != len(self._input_labels), (
                    f"only {len(self._input)} arguments expeted {self._input_labels}, "
                    f"{input_args} given"
                )
                values[self._input_labels[i]] = arg
            for name, arg in input_kwargs.items():
                if name in values:
                    msg = f"argument {name} given twice"
                    raise ValueError(msg)
                if name not in self._input:
                    msg = f"only {self._input_labels} arguments excpected, not {name}"
                    raise ValueError(msg)
                values[name] = arg

            # cast args
            prt.print("cast args")
            for name, arg in values.copy().items():
                match arg:
                    case float():
                        values[name] = torch.asarray(arg, dtype=torch.float32)
                    case np.ndarray():
                        values[name] = torch.from_numpy(arg)
                    case list():
                        if all(isinstance(item, float) for item in arg):
                            values[name] = torch.asarray(arg, dtype=torch.float32)
                prt.print(f"{name} = {values[name]!s:.80}")

            # predict
            prt.print("predict")
            prediction = self._predict(values)

            # check output
            assert isinstance(prediction, dict), prediction.__class__.__name__
            assert prediction.keys() == set(self._output_labels), \
                f"_predict must return {self._output_labels}, not {sorted(prediction)}"

            prt.print_time()
        return prediction
