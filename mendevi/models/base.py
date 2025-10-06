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
        input : list[str]
            The name of all input parameters.
            The possibles values are :py:cst:`mendevi.plot.axis.Name`.
        output : list[str]
            The name of all output parameters.
            The possibles values are :py:cst:`mendevi.plot.axis.Name`.
        parameters : torch.Tensor, optional
            The learnable parameters for regressive models.
        """
        # check input output
        assert hasattr(input, "__iter__"), input.__class__.__name__
        assert hasattr(output, "__iter__"), output.__class__.__name__
        input, output = list(input), list(output)
        assert input, "input must be not empty"
        assert output, "output must be not empty"
        assert all(isinstance(lab, str) and lab in LABELS for lab in input), input
        assert all(isinstance(lab, str) and lab in LABELS for lab in output), output
        self._input = input
        self._output = output

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
        self._authors = authors

    def _fit(self, input: dict[str]):
        """Perform regression on parameters ``self.parameters``."""
        raise NotImplementedError

    @abc.abstractmethod
    def _predict(self, input: dict[str]) -> dict[str]:
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

        Paremeters
        ----------
        input : dict[str]
            The parameters values, with the keys defined during initialisation.

        Returns
        -------
        prediction : dict[str]
            Associate each ouput variable with the prediction.
        """
        # check args
        input: dict[str] = {}
        for i, arg in enumerate(input_args):
            if i == len(self._input):
                raise ValueError(
                    f"only {len(self._input)} arguments expeted {self._input}, {input_args} given"
                )
            input[self._input[i]] = arg
        for name, arg in input_kwargs.items():
            if name in input:
                raise ValueError(f"argument {name} given twice")
            if name not in self._input:
                raise ValueError(f"only {self._input} arguments excpected, not {name}")
            input[name] = arg

        # cast args
        for name, arg in input.copy().items():
            match arg:
                case float():
                    input[name] = torch.asarray(arg, dtype=torch.float32)
                case np.ndarray():
                    input[name] = torch.from_numpy(arg)
                case list():
                    if all(isinstance(item, float) for item in arg):
                        input[name] = torch.asarray(arg, dtype=torch.float32)

        # predict
        prediction = self._predict(input)

        # chack output
        assert isinstance(prediction, dict), prediction.__class__.__name__
        assert prediction.key() == set(self._output), \
            f"_predict must return {self._output}, not {sorted(prediction)}"

        return prediction
