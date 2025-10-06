#!/usr/bin/env python3

"""Unify all the models with a common sctucture."""

import abc.ABC
import pathlib
import typing

import torch


class Model(abc.ABC):
    """Common structure to all models.

    Attributes
    ----------
    cite : str
        The latex bibtext model citation.
    parameters : torch.Tensor | None
        The trainable parameters of the model.
    """

    def __init__(self,
        title: typing.Optional[str] = None,
        authors: typing.Iterable[str] = None,
        input: typing.Iterable[str] = None,
        output: typing.Iterable[str] = None,
        parameters: typing.Optional[torch.Tensor] = None
    ):
        """Initialise the model.

        Parameters
        ----------
        title : str, optional
            The model title.
        authors : list[str]
            The list of the authors the have created that model.
        input : list[str]
            The name of all input parameters.
            The possibles values are :py:cst:`mendevi.plot.axis.Name`.
        output : list[str]
            The name of all output parameters.
            The possibles values are :py:cst:`mendevi.plot.axis.Name`.
        parameters : torch.Tensor, optional
            The learnable parameters for regressive models.
        """
        raise NotImplementedError

    @abc.abstractmethod  # TODO: make abstract only if self.parameters is not None
    def _fit(input: dict[str]):
        """Perform regression on parameters ``self.parameters``."""
        raise NotImplementedError

    @abc.abstractmethod
    def _predict(input: dict[str]) -> dict[str]:
        """The heart of the model."""
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
        if self.parameters is None:  # TODO: use a metaclass to avoid fit method creation
            raise RuntimeError("This model is not trainable.")
        # TODO: raise exception if already fitted on that database.
        # TODO: read database and check
        self._fit(...)
        # TODO: chec the state of self.parameters
        return self

    def predict(self, input: dict[str]) -> dict[str]:
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
        # TODO: check the input var name
        # TODO: cast values into torch Tensor
        prediction = self._predict(...)
        # TODO: check output detype, var name...
        # TODO: homogeneous recast of output
        return prediction
