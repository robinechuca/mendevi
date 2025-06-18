#!/usr/bin/env python3

"""Structure of a scalar to represent the value of a physical quantity.

Defines a scalar physical quantity to avoid omogeneity errors by being very clear about the units,
then helps propagate uncertainties.

The motivation is to help to be clear on the normalisation rules.
"""

import math
import numbers
import re
import typing

import sympy


class Scalar:
    """A constant scalar to represent the value of a physical quantity.

    Attributes
    ----------
    avg : float
        The value of itself (readonly).
    std : float
        The standard deviation (readonly).

    Examples
    --------
    >>> from mendevi.scalar import Scalar
    >>> (nbr := Scalar(1/3, std=0.01))
    Scalar(0.3333333333333333, std=0.01)
    >>> print(nbr)
    0.33 \xb1 0.03
    >>> nbr.std
    0.01
    >>>
    >>> Scalar(nbr)  # copy data
    Scalar(0.3333333333333333, std=0.01)
    >>>
    """

    def __init__(
        self,
        avg: numbers.Real | str | typing.Self,
        *,
        std: numbers.Real | str=0,
    ):
        """Initialise the attributes."""
        if isinstance(avg, self.__class__):  # from a Scalar
            self._avg, self._std, self._unit = avg._avg, avg._std, avg._unit
        else:
            self._avg = float(avg)
            self._std = float(std)
            assert self._std >= 0, f"the standard deviation ({std}) has to be >=0"

    def __add__(self, other: numbers.Real | str | typing.Self) -> typing.Self:
        """Add self and other, assuming they are following 2 normal independant laws."""
        try:
            other = Scalar(other)
        except ValueError:
            return NotImplemented
        avg = self._avg + other._avg  # E[X1+X2] = E[x1]+E[X2]
        std = math.sqrt(self._std**2 + other._std**2)
        return self.__class__(avg, std=std)

    def __eq__(self, other: typing.Self) -> bool:
        """For hash table."""
        return self._avg == Scalar(other).avg

    def __float__(self) -> float:
        """Convert into single float."""
        return self._avg

    def __hash__(self) -> int:
        """Imuable hash table behavor."""
        return hash((self._avg, self._std))

    def __mul__(self, other: numbers.Real | str | typing.Self) -> typing.Self:
        """Multiply self and other, assuming they are following 2 normal independant laws.

        Examples
        --------
        >>> from lca.classes.scalar import Scalar
        >>> Scalar(2, std=1/2) * Scalar(4, std=1/2)
        Scalar(8.0, std=2.25)
        >>>
        """
        try:
            other = Scalar(other)
        except ValueError:
            return NotImplemented
        avg = self._avg * other._avg  # E[X1.X2] = E[X1].E[X2]
        var1, var2 = self._std * self._std, other._std * other._std
        mu12, mu22 = self._avg * self._avg, other._avg * other._avg
        std = math.sqrt(var1*var2 + var1*mu22 + var2*mu12)  # V[X1.X2] = E[X1.X1.X2.X2]-E[X1.X2]**2
        return self.__class__(avg, std=std)

    def __radd__(self, other: numbers.Real | str | typing.Self) -> typing.Self:
        """Addition is commutative."""
        return self.__add__(other)

    def __repr__(self) -> str:
        """Gives a nice evaluable representation of itself."""
        args = [str(self._avg)]
        if self._std != 0:
            args.append(f"std={self._std}")
        return f"{self.__class__.__name__}({', '.join(args)})"

    def __rmul__(self, other: numbers.Real | str | typing.Self) -> typing.Self:
        """Product is commutative."""
        return self.__mul__(other)

    def __str__(self) -> str:
        """Gives a nice compact representation of itself."""
        out = f"{float(self):.2g}"
        if self._std != 0:
            out += f" \xb1 {3*self._std:.2g}"  # utf8 "b1" is +- symbol
        if self._unit != 1:
            out += f" {self._unit}"
        return out

    @property
    def avg(self) -> float:
        """The representative value as a float number."""
        return self._avg

    @property
    def std(self) -> float:
        """The standard deviation."""
        return self._std
