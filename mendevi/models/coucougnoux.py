#!/usr/bin/env python3

"""A stupid test model."""

from mendevi.models import Model


class Coucougnoux(Model):
    """Test model."""

    def __init__(self):
        super().__init__("A test model", input_labels=["threads"], output_labels=["power"])

    def _fit(self, values: dict[str]):
        """Fit the stupid model.

        Examples
        --------
        >>> from mendevi.models.coucougnoux import Coucougnoux
        >>> model = Coucougnoux()
        >>> model.fit("mendevi.db")
        >>>
        """
        print(values)

    def _predict(self, values: dict[str]) -> dict[str]:
        pass
