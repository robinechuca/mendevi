"""Test the different ways to instanciate the bastract Model class."""

import pytest

from mendevi.models import Model

DEFAULT_KWARGS = {
    "input_labels": ["quality"],
    "output_labels": ["psnr"],
}


def test_no_instanciable_missing() -> None:
    """Make sure it it abstract."""

    class MyModelNothing(Model):
        pass

    class MyModelFit(Model):
        _fit = None

    class MyModelPredict(Model):
        _predict = None

    with pytest.raises(
        TypeError,
        match=r"Can't instanciate abstract class MyModelNothing",
    ):
        MyModelNothing(**DEFAULT_KWARGS)

    with pytest.raises(
        TypeError,
        match=r"Can't instanciate abstract class MyModelFit",
    ):
        MyModelFit(**DEFAULT_KWARGS)

    with pytest.raises(
        TypeError,
        match=r"Can't instanciate abstract class MyModelPredict",
    ):
        MyModelPredict(**DEFAULT_KWARGS)


def test_no_instanciable_exces() -> None:
    """Make sure it it abstract."""

    class MyModelFit(Model):
        _fit = None
        _predict = None
        _fit_vect = None

    class MyModelPredict(Model):
        _fit = None
        _predict = None
        _predict_vect = None

    with pytest.raises(
        TypeError,
        match=r"Can't instanciate abstract class MyModelFit",
    ):
        MyModelFit(**DEFAULT_KWARGS)

    with pytest.raises(
        TypeError,
        match=r"Can't instanciate abstract class MyModelPredict",
    ):
        MyModelPredict(**DEFAULT_KWARGS)


def test_instanciable() -> None:
    """Test to instanciate only 1 of the 3 methods."""

    class ModelFit(Model):
        _fit = None
        _predict = None

    class ModelFitVect(Model):
        _fit_vect = None
        _predict = None

    class ModelFitVectNorm(Model):
        _fit_vect_norm = None
        _predict = None

    class ModelPredict(Model):
        _fit = None
        _predict = None

    class ModelPredictVect(Model):
        _fit = None
        _predict_vect = None

    class ModelPredictVectNorm(Model):
        _fit = None
        _predict_vect_norm = None

    ModelFit(**DEFAULT_KWARGS)
    ModelFitVect(**DEFAULT_KWARGS)
    ModelFitVectNorm(**DEFAULT_KWARGS)
    ModelPredict(**DEFAULT_KWARGS)
    ModelPredictVect(**DEFAULT_KWARGS)
    ModelPredictVectNorm(**DEFAULT_KWARGS)
