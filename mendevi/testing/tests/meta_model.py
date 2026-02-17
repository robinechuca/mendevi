"""Test the different ways to instanciate the bastract Model class."""

import pytest

from mendevi.models import Model

DEFAULT_KWARGS = {
    "input_labels": ["quality"],
    "output_labels": ["psnr"],
}


def test_no_instanciable() -> None:
    """Make sure it it abstract."""

    class MyModel(Model):
        pass

    with pytest.raises(
        TypeError,
        match=r"Can't instanciate abstract class MyModel",
    ):
        MyModel(**DEFAULT_KWARGS)


def test_instanciable() -> None:
    """Test to instanciate only 1 of the 3 methods."""

    class ModelPredict(Model):
        _predict = None

    class ModelPredictVect(Model):
        _predict_vect = None

    class ModelPredictVectNorm(Model):
        _predict_vect_norm = None

    ModelPredict(**DEFAULT_KWARGS)
    ModelPredictVect(**DEFAULT_KWARGS)
    ModelPredictVectNorm(**DEFAULT_KWARGS)
