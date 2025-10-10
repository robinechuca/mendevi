#!/usr/bin/env python3

"""Unify all the models with a common sctucture."""

import abc.ABC
import pathlib
import typing

import numpy as np
import torch

from mendevi.cst.labels import LABELS
from mendevi.database.create import is_sqlite


class Model(abc.ABC):
    """Common structure to all models.

    Attributes
    ----------
    cite : str
        The latex bibtext model citation.
    parameters : torch.Tensor | None
        The trainable parameters of the model (read and write).
    TODO: ajouter labels input output
    """

    def __init__(
        self,
        title: typing.Optional[str] = None,
        sources: str = "",
        input_labels: typing.Iterable[str] = None,
        output_labels: typing.Iterable[str] = None,
        parameters: typing.Optional[torch.Tensor] = None,
    ):
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
        # check input output
        assert hasattr(input_labels, "__iter__"), input_labels.__class__.__name__
        assert hasattr(output_labels, "__iter__"), output_labels.__class__.__name__
        input_labels, output_labels = list(input_labels), list(output_labels)
        assert input_labels, "input must be not empty"
        assert output_labels, "output must be not empty"
        assert all(isinstance(lab, str) and lab in LABELS for lab in input_labels), input_labels
        assert all(isinstance(lab, str) and lab in LABELS for lab in output_labels), output_labels
        self._input_labels = input_labels
        self._output_labels = output_labels

        # check parameters
        if parameters is not None:
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

    def fit(self, database: pathlib.Path | str) -> typing.Self:
        """Fit the trainable hyper parameters of the models.

        Parameters
        ----------
        database : pathlike
            The training database.

        Return
        ------
        self
            A reference to the inplace fitted model.
        """
        if self._parameters is None:
            raise RuntimeError("This model is not trainable.")
        database = pathlib.Path(database).expanduser()
        assert is_sqlite(database), f"{database} is not a valid SQL database"

        raise NotImplementedError
        # TODO: read database and check
        self._fit(...)
        # TODO: chec the state of self.parameters
        return self

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
