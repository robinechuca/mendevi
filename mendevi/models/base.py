"""Unify all the models with a common sctucture."""

import abc
import logging
import numbers
import pathlib
import re
import sqlite3
import tempfile
import typing

import numpy as np
import torch
from context_verbose import Printer

from mendevi.cst.encoders import ENCODERS
from mendevi.cst.labels import LABELS
from mendevi.cst.profiles import PROFILES
from mendevi.database.create import create_database, is_sqlite
from mendevi.database.extract import SqlLinker
from mendevi.database.meta import get_extractor, merge_extractors
from mendevi.download.decapsulation import retrive_file
from mendevi.exceptions import RejectError
from mendevi.probe import probe_and_store
from mendevi.utils import compute_video_hash

EPS = torch.finfo(torch.float32).eps


def to_torch(data: dict[str, list], dtype: torch.dtype = torch.float32) -> dict[str, torch.Tensor]:
    """Convert the fields into a tensor compatible encoding.

    Allows you to cast lists of numbers into floating point vectors.
    Labels are encoded as one-hot.

    Returns
    -------
    dict[str, torch.Tensor]
        For each starting field, associate the torch matrix of size (n, k),
        where n is the number of elements and k is the dimension.
        k is 1 for lists of numbers and is the cardinality of the number of labels otherwise.

    Examples
    --------
    >>> from pprint import pprint
    >>> from mendevi.models.base import to_torch
    >>> data = {
    ...     "effort": ["fast", "medium", "slow"],
    ...     "encoder": ["libx264", "libsvtav1"],
    ...     "profile": ["sd", "hd", "fhd"],
    ...     "scalar": [0.0, 1.0, 2.0],
    ... }
    >>> pprint(to_torch(data))
    {'effort': tensor([[1., 0., 0.],
            [0., 1., 0.],
            [0., 0., 1.]]),
     'encoder': tensor([[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 1., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0.]]),
     'profile': tensor([[0., 0., 1., 0.],
            [0., 1., 0., 0.],
            [1., 0., 0., 0.]]),
     'scalar': tensor([[0.],
            [1.],
            [2.]])}
    >>>

    """
    assert isinstance(data, dict), data.__class__.__name__

    out_data: dict[str, torch.Tensor] = {}
    for name, values in data.items():
        assert isinstance(values, list), values.__class__.__name__
        match name:
            case "effort":
                out_data["effort"] = torch.nn.functional.one_hot(
                    torch.asarray(
                        [{"fast": 0, "medium": 1, "slow": 2}[e] for e in values], dtype=int,
                    ),
                    num_classes=3,
                ).to(dtype)
            case "encoder":
                encoders = {e: i for i, e in enumerate(sorted(ENCODERS))}
                out_data["encoder"] = torch.nn.functional.one_hot(
                    torch.asarray([encoders[e] for e in values], dtype=int),
                    num_classes=len(encoders),
                ).to(dtype)
            case "profile":
                profiles = {e: i for i, e in enumerate(sorted(PROFILES))}
                out_data["profile"] = torch.nn.functional.one_hot(
                    torch.asarray([profiles[e] for e in values], dtype=int),
                    num_classes=len(profiles),
                ).to(dtype)
            case "mode":
                out_data["mode"] = torch.nn.functional.one_hot(
                    torch.asarray([{"cbr": 0, "vbr": 1}[e] for e in values], dtype=int),
                    num_classes=2,
                ).to(dtype)
            case "hostname":
                msg = "The one hot encoding for hostname is not defined."
                raise NotImplementedError(msg)
            case _:
                assert all(isinstance(v, numbers.Real) for v in values), values
                out_data[name] = torch.asarray(values, dtype=dtype)[:, None]
    return out_data


def from_torch(data: dict[str, torch.Tensor]) -> dict[str, list]:
    """Back convertion from vectorized torch to python list, bijection of :py:func:`to_torch`."""
    out_data: dict[str, list] = {}
    for name, values in data.items():
        assert isinstance(values, torch.Tensor), values.__class__.__name__
        assert values.ndim == 2, values.shape
        match name:
            case "effort" | "encoder" | "profile" | "mode" | "hostname":
                raise NotImplementedError
            case _:
                out_data[name] = values.squeeze(1).tolist()
    return out_data


class MetaModel(abc.ABCMeta):
    """Relax somes+ constraints on few methods.

    see https://github.com/python/cpython/blob/main/Lib/_py_abc.py
    and https://github.com/python/cpython/blob/main/Lib/abc.py
    """

    def __call__(cls, *args: tuple, **kwargs: dict) -> typing.ClassVar:
        """Relax abstraction constraints on interconnected methods."""
        for group in [
            ("_predict", "_predict_vect", "_predict_vect_norm"),
            ("_fit", "_fit_vect", "_fit_vect_norm"),
        ]:
            # get implemented methods
            abstracts = {
                name: getattr(getattr(cls, name, None), "__isabstractmethod__", False)
                for name in group
            }
            # verification
            if all(abstracts.values()):
                msg = (
                    f"Can't instanciate abstract class {cls.__name__} "
                    "without an implementation for any of the abstract method "
                    f"{' '.join(f'{n!r}' for n in abstracts)}"
                )
                raise TypeError(msg)
            if list(abstracts.values()).count(False) != 1:
                msg = (
                    f"Can't instanciate abstract class {cls.__name__} "
                    "without more than one implementation of the abstract method "
                    f"{' '.join(f'{n!r}' for n in group)}"
                )
                raise TypeError(msg)
            # cleaning
            cls.__abstractmethods__ = cls.__abstractmethods__ - frozenset(group)
        return super().__call__(*args, **kwargs)


class Model(metaclass=MetaModel):
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
    accuracy : dict[str, float]
        For each output label, associate the standard deviation of the associated average error.
        This dictionary is constructed when the .fit method is called (readonly).

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
        self._std_mean: dict = {}
        self._accuracy: dict | None = None

        # check title
        if title is None:
            title = (
                f"{'regressive ' if self._parameters is not None else ''}model "
                f"to predict {', '.join(sorted(self._output_labels))} "
                f"from {', '.join(sorted(self._input_labels))}"
            )
        else:
            assert isinstance(title, str), title.__class__.__name__
        self._title = title

        # check authors
        sources = kwargs.get("sources", "")
        assert isinstance(sources, str), sources.__class__.__name__
        self._sources = sources

    @abc.abstractmethod
    def _fit(self, values: dict[str]) -> None:
        """Perform data regression to find the model's hyperparameters.

        Hyperparameters must be added to the ``self.parameters`` dictionary.

        Parameters
        ----------
        values: dict[str, list]
            For each input and output label (ie self.input_labels union self.output_labels),
            associate the list of corresponding values.

        Notes
        -----
        If the model contains hyperparameters,
        it is essential that the child class redefines one of the methods
        self._fit, self._fit_vect or self._fit_vect_norm.

        """
        # level 1
        if (
            self.__class__._fit_vect is not Model._fit_vect  # noqa: SLF001
            or self.__class__._fit_vect_norm is not Model._fit_vect_norm  # noqa: SLF001
        ):
            self._fit_vect(to_torch(values))

        # level 0
        else:
            raise NotImplementedError

    @abc.abstractmethod
    def _fit_vect(self, values: dict[str, torch.Tensor]) -> None:
        """Do the same as ``self._fit``, but provide tensor rather than lists."""
        # level 2
        if self.__class__._fit_vect_norm is not Model._fit_vect_norm:  # noqa: SLF001
            assert set(self._input_labels) | set(self._output_labels) == set(values)
            self._std_mean = {
                name: (
                    torch.std_mean(data, dim=0, keepdim=True)
                    if data.shape[1] == 1 else
                    (1.0, 0.0)  # do nothing for onehot encoding
                )
                for name, data in values.items()
            }
            self._fit_vect_norm(
                {
                    name: (data - self._std_mean[name][1]) / (self._std_mean[name][0] + EPS)
                    for name, data in values.items()
                },
            )

        # level 1
        else:
            raise NotImplementedError

    @abc.abstractmethod
    def _fit_vect_norm(self, values: dict[str, torch.Tensor]) -> None:
        """Do the same as ``self._fit_vect``, but the tensors are centered and reduced."""
        raise NotImplementedError

    @abc.abstractmethod
    def _predict(self, values: dict[str, list]) -> dict[str, list]:
        """Perform model prediction.

        Parameters
        ----------
        values: dict[str, list]
            For each input label (ie self.input_labels), associate the list of corresponding values.

        Returns
        -------
        output: dict[str, list]
            For each ouput label (ie self.output_labels),
            associate the list of corresponding predicted values.

        Notes
        -----
        The child class must to redefines one of the methods
        self._predict, self._predict_vect or self._predict_vect_norm.

        """
        # level 1
        if (
            self.__class__._predict_vect is not Model._predict_vect  # noqa: SLF001
            or self.__class__._predict_vect_norm is not Model._predict_vect_norm  # noqa: SLF001
        ):
            return from_torch(self._predict_vect(to_torch(values)))

        # level 0
        raise NotImplementedError

    @abc.abstractmethod
    def _predict_vect(self, values: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        """Do the same as ``self._predict``, but provide and return tensor rather than lists.

        Input and output tensors for scalar fields are column vectors, of shape (n, 1).
        """
        # level 2
        if self.__class__._predict_vect_norm is not Model._predict_vect_norm:  # noqa: SLF001
            assert set(values).issubset(set(self._input_labels)), (values, self._input_labels)
            assert self._std_mean, "you must to call fit before predict"
            norm_prediction = self._predict_vect_norm(
                {
                    name: (data - self._std_mean[name][1]) / (self._std_mean[name][0] + EPS)
                    for name, data in values.items()
                },
            )
            assert set(self._output_labels) == set(norm_prediction)
            return {
                name: (
                    norm_prediction[name] * (self._std_mean[name][0]+EPS) + self._std_mean[name][1]
                )
                for name in self._output_labels
            }

        # level 1
        raise NotImplementedError

    @abc.abstractmethod
    def _predict_vect_norm(self, values: dict[str, torch.Tensor]) -> dict[str]:
        """Implement the heart of the model."""
        raise NotImplementedError

    @property
    def accuracy(self) -> dict[str, float]:
        """Return the error std for each output label."""
        if self._accuracy is None:
            msg = "you must call the .fit method before you can know the accuracy of the model"
            return RuntimeError(msg)
        return self._accuracy.copy()  # copy for readonly

    @property
    def cite(self) -> str:
        """Return the bibtex citation."""
        raise NotImplementedError

    def extract_video_props(self, video: pathlib.Path | str) -> dict[str]:
        """Excerpt from the video, useful settings for the model.

        Parameters
        ----------
        video : pathlike
            The path to the video whose behavior we want to ``predict``.

        Returns
        -------
        properties : dict[str]
            For relevant input labels,
            associate the corresponding properties of the video provided as a parameter.

        """
        # To avoid redundancy, and thus be able to use the rest of the API,
        # the decision was made to call the probe function on the video
        # rather than extracting the parameters manually.
        # We therefore create a small temporary database
        # that allows us to reuse the other main functions of mendevi to serve this purpose.

        video = pathlib.Path(video).expanduser()
        assert video.exists(), video

        # 1) creation of the database
        database = pathlib.Path(tempfile.gettempdir()) / "model.db"
        if not database.exists():
            create_database(database)

        # 2) find the parameters for probe
        atom_names, _ = merge_extractors(set(self._input_labels), return_callable=False)
        probe_kwargs = {
            metric: metric in atom_names
            for metric in ("rms_sobel", "rms_time_diff", "spatial_dct", "temporal_dct", "uvq")
        } | {"ref": {}}  # required by probe_and_store (for comparative metrics)

        # 3) call probe
        if (conn := probe_and_store(database, video, **probe_kwargs)) is not None:
            conn.close()

        # 4) select lthe labels deducible from probe
        # to verify that a value can be extracted from probe,
        # we check whether the code that extracts it only calls on the t_vid_video table.
        input_labels = {
            lbl for lbl in self._input_labels if all(  # return also True if empty -> ok
                select.split(".")[0] in {"t_vid_video", "t_src_video", "t_dst_video"}
                for atom_lbl in merge_extractors({lbl})[0]
                for select in getattr(get_extractor(lbl, safe=True).func, "select", [])
            )
        }

        # 5) extract fields from SQL database
        vid_id: bytes = compute_video_hash(video)
        _, line_extractor = merge_extractors(input_labels, return_callable=True)
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            raw = conn.execute("SELECT * FROM t_vid_video WHERE vid_id = ?", (vid_id,)).fetchone()
            return line_extractor(dict(raw))

    def fit(
        self,
        database: pathlib.Path | str,
        select: str | None = None,
        query: str | None = None,
        table: str | None = None,
    ) -> typing.Self:
        """Fit the trainable hyper parameters of the model.

        Parameters
        ----------
        database : pathlike
            The training database.
        select : str, optional
            The python expression to keep the line, like ``mendevi plot --filter``.
        query : str, optional
            If provided, use this sql query to perform the request,
            otherwise (default) attemps to guess the query.
        table : str, optional
            The main sql table juste after the FROM in SELECT.
            It helps to choose the write query when there is several candidates.

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
            prt.print("get SQL extractor")
            atom_names, line_extractor = merge_extractors(
                set(self._input_labels) | set(self._output_labels),
                select=select,
                return_callable=True,
            )
            if query is None:
                # search all SQL queries
                select = {s for lbl in atom_names for s in get_extractor(lbl).func.select}
                if len(queries := SqlLinker(*select).sql) == 0:
                    msg = "fail to create the SQL query, please provide it yourself"
                    raise RuntimeError(msg)

                # select good query
                if table is not None:
                    queries = {re.search(r"FROM\s+(?P<tab>\w+)", q)["tab"]: q for q in queries}
                    if table not in queries:
                        msg = f"possible queries from {', '.join(queries)}, not {table}"
                        raise ValueError(msg)
                    queries = [queries[table]]

                # warning
                if len(queries) > 1:
                    logging.getLogger(__name__).warning(
                        "several request founded %s, please provide the table or the request",
                        queries,
                    )
                query = queries.pop(0)
            else:
                assert isinstance(query, str), query.__class__.__name__

            # perform sql request
            prt.print("perform SQL query")
            values = {label: [] for label in set(self._input_labels) | set(self._output_labels)}
            with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as conn:
                conn.row_factory = sqlite3.Row
                for raw in conn.execute(query):
                    try:
                        for label, value in line_extractor(dict(raw)).items():
                            values[label].append(value)
                    except RejectError:
                        pass

            # fit the model
            prt.print("fit the model")
            self._fit(values)

            # evaluate the model error
            with prt("Model accuracy:"):
                prediction = to_torch(
                    self._predict({lbl: values[lbl] for lbl in self._input_labels}),
                )
                validation = to_torch({lbl: values[lbl] for lbl in self._output_labels})
                self._accuracy = {
                    name: float(((prediction[name] - validation[name])**2).mean().sqrt())
                    for name in self._output_labels
                }
                for atom_names, std_err in self._accuracy.items():
                    prt.print(f"std of {atom_names}: {std_err:.4g}")

            prt.print_time()
        return self

    @property
    def input_labels(self) -> list[str]:
        """Return the name of all input parameters."""
        return self._input_labels.copy()

    def is_fit(self) -> bool:
        """Return True if the method `fit` has been succesfully called."""
        return self._accuracy is not None

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
            logging.getLogger(__name__).warning("change the type of parameters")
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
                if name not in self._input_labels:
                    msg = f"only {self._input_labels} arguments excpected, not {name}"
                    raise ValueError(msg)
                values[name] = arg

            # cast args to list
            prt.print("vectorize args")
            values = self.vectorize_kwargs(values)
            # for name, arg in values.items():
            #     prt.print(f"{name} = {arg!s:.80}")

            # predict
            prt.print("predict")
            prediction = self._predict(values)

            # check output
            assert isinstance(prediction, dict), prediction.__class__.__name__
            assert prediction.keys() == set(self._output_labels), \
                f"_predict must return {self._output_labels}, not {sorted(prediction)}"

            prt.print_time()
        return prediction

    def predict_from_video(
        self, video: pathlib.Path | str, *args: tuple, **kwargs: dict,
    ) -> dict[str]:
        """Simplify the predict method by automatically extracting parameters from the video.

        Parameters
        ----------
        video : pathlike
            Transmitted to self.extract_video_props.
        *args, **kwargs, optional
            The other arguments are passed to the prdict method.
            Accept a list of arguments for vectorization.
            Single values are duplicated in a list of the same length as the longest one.

        Returns
        -------
        prediction : dict[str]
            The value returned by the ``predict`` method.

        """
        vid_kwargs = self.extract_video_props(video)
        return self.predict(*args, **kwargs, **vid_kwargs)

    @staticmethod
    def vectorize_kwargs(kwargs: dict[str], *, _skip_duplication: bool = False) -> dict[str]:
        """Help for predict method."""
        assert isinstance(kwargs, dict), kwargs.__class__.__name__
        assert isinstance(_skip_duplication, bool), _skip_duplication.__class__.__name__
        vect_kwargs: dict[str] = kwargs.copy()

        # cast args to list
        for name, arg in kwargs.items():
            match arg:
                case numbers.Real() | str():
                    vect_kwargs[name] = [arg]
                case np.ndarray() | torch.Tensor():
                    vect_kwargs[name] = arg.tolist()
                case tuple() | set():
                    vect_kwargs[name] = list(arg)

        # duplicate singloton args
        if _skip_duplication:
            return vect_kwargs
        size = max(map(len, vect_kwargs.values()), default=1)
        return {name: arg * size if len(arg) == 1 else arg for name, arg in vect_kwargs.items()}
