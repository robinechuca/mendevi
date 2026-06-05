"""All measurement helper."""

import contextlib
import numbers
import platform
import queue
import threading
import time
import typing

import numpy as np

from .adecwatts import ADECWattmeter
from .g5kpower import g5kpower
from .gpu import UsageGPU
from .psutil import Usage
from .rapl import RAPL

G5K_API_WAIT = 5.0  # waiting time (in sec) before data from the grid5000 API becomes accessible


class Activity(threading.Thread):
    """Measure the computer activity of a section.

    Examples
    --------
    >>> import pprint, time
    >>> from mendevi.measures import Activity
    >>> with Activity() as activity:
    ...     time.sleep(0.1)
    ...     activity.start_slice("lbl 1")
    ...     time.sleep(0.2)
    ...     _ = activity.stop_slice()
    ...     activity.start_slice("lbl 2")
    ...     time.sleep(0.3)
    ...     activity.start_slice("lbl 3")
    ...     time.sleep(0.4)
    ...
    >>> slices, full = activity.get_slices(), activity.get_full()
    >>> round(full["duration"], 2)
    1.0
    >>> sorted(slices)
    ['lbl 1', 'lbl 2', 'lbl 3']
    >>> round(slices["lbl 2"]["duration"], 2)
    0.3
    >>>

    """

    def __init__(self, sleep: numbers.Real = 50e-3) -> None:
        """Init the perf context.

        Parameters
        ----------
        sleep : float, default=50e-3
            The time interval between 2 measures (in s).

        """
        assert isinstance(sleep, numbers.Real), sleep.__class__.__name__
        assert sleep > 0, sleep

        super().__init__(daemon=True)

        self._adec_catcher = ADECWattmeter(no_fail=True)
        self._rapl_catcher = RAPL(sleep=sleep, no_fail=True)
        self._usage_catcher = Usage(sleep=sleep)
        self._usage_gpu_catcher = UsageGPU(sleep=sleep)
        self._exit_queue = queue.Queue()
        self._slices: dict[typing.Hashable, list[float, float]] = {}  # {lbl: [start, stop], ...}
        self._slices_current_lbl: typing.Hashable | None = None  # the currently processing label
        self._as_dict_called: bool = False
        self.sleep = float(sleep)
        self.res: dict = {}

    def get_full(self) -> dict | tuple[dict, dict]:
        """Collect the data and return the full activity.

        Returns
        -------
        activity: dict[str]
            * duration: float, the real measure duration.
            * gpu_core: list[list[float]], tensor of detailed usage of each GPU in [0, 1].
            * gpu_core_avg: float, the sum of the average usage of each GPU.
            * gpu_dt: list[float], the duration of each interval (in s).
            * gpu_power: list[list[float]], the sampled power in each point (in W).
            * gpu_power_avg: float, the total power consumption of all GPU (in W).
            * ps_core: float, the mean cummulated usage of all the logical cpus.
            * ps_cores: list[list[float]], tensor of detailed usage of each logical core in %.
            * ps_dt: list[float], the duration of each interval (in s).
            * ps_ram: list[int], list of the sampled ram usage in bytes in each point.
            * ps_temp: dict[str, lis[float]], the temperature of each device (in C).
            * rapl_dt: list[float], the duration of each interval (in s).
            * rapl_energy: float, the total energy consumption (in J).
            * rapl_power: float, the average power, energy divided by the duration (in W).
            * rapl_powers: list[float], the average power in each interval (in W).
            * start: float, absolute timestamp.
            * wattmeter_dt: list[float], the duration of each interval (in s).
            * wattmeter_energy: float, the total energy consumption (in J).
            * wattmeter_power: float, the average power, energy divided by the duration (in W).
            * wattmeter_powers: list[float], the sampled power in watt in each point.

        """
        self.get_slices()
        return self.res[1]

    def get_slices(self) -> dict[str, dict]:
        """For each slices initialized by start_slice, are returned here.

        Returns
        -------
        slices : dict[str, dict]
            For each label given in ``start_slice``,
            return the same dict as :py:meth:`get_full` for this specific slice.

        """
        # stop measurements
        if self._as_dict_called:
            return self.res[0]
        self._as_dict_called = True
        self.join()
        # request wattmeter power
        if "wattmeter_dt" not in self.res:  # ADEC and GRID'5000 are mutualy exclusive
            time.sleep(max(
                0.0,
                G5K_API_WAIT + self.res["start"] + self.res["duration"] - time.time(),
            ))
            try:
                wattmeter = g5kpower(platform.node(), self.res["start"], self.res["duration"])
            except ValueError:
                wattmeter = None
            else:
                self.res |= {
                    "wattmeter_dt": wattmeter["dt"],
                    "wattmeter_power": wattmeter["power"],
                }
        # cut slices
        dtlbl_datalbls = (
            ("ps_dt", ("ps_core", "ps_ram", "ps_temp")),
            ("rapl_dt", ("rapl_power",)),
            ("gpu_dt", ("gpu_core", "gpu_memory", "gpu_power")),
            ("wattmeter_dt", ("wattmeter_power",)),
        )
        dtlbl_datalbls = tuple((dt, fields) for dt, fields in dtlbl_datalbls if dt in self.res)
        if self._slices:
            slices = {  # each slice, not concats
                slicelbl: {
                    **{
                        fieldlbl: data
                        for dt_lbl, data_lbls in dtlbl_datalbls
                        for fieldlbl, data in self._extract_slice(
                            dt_lbl, data_lbls, start, stop,
                        ).items()
                    },
                    "start": start,
                    "duration": stop-start,
                }
                for slicelbl, (start, stop) in self._slices.items()
            }
            # add the avg values
            slices = {  # for slices
                slicelbl: {
                    **data,  # keep the expanded data
                    **{  # add the averages
                        f"{flbl}_avg": self._trapez_integral_avg(data[dtlbl], data[flbl])
                        for dtlbl, fieldlbls in dtlbl_datalbls for flbl in fieldlbls
                    },
                }
                for slicelbl, data in slices.items()
            }
            self.res = (slices, self.res)
        else:
            self.res = ({}, self.res)
        return self.res[0]

    def run(self) -> None:
        """Perform the measures."""
        self.res["start"] = time.time()
        with (
            self._adec_catcher as adec,
            self._rapl_catcher as rapl,
            self._usage_catcher as usage,
            self._usage_gpu_catcher as gpu,
        ):
            self._exit_queue.get()  # wait
        self.res |= {
            "ps_core": usage["cpu"],
            "ps_dt": usage["dt"],
            "ps_ram": usage["ram"],
            "ps_temp": usage["temp"],
        }
        if adec is not None:
            self.res |= {
                "wattmeter_dt": adec["dt"],
                "wattmeter_power": [sum(p) for p in adec["p_eff"]],
            }
            print(self.res["wattmeter_power"])
        if rapl is not None:
            self.res |= {
                "rapl_dt": rapl["dt"],
                "rapl_power": rapl["power"],
            }
        if gpu is not None:
            self.res |= {
                "gpu_core": gpu["gpu"],
                "gpu_dt": gpu["dt"],
                "gpu_memory": gpu["memory"],
                "gpu_power": gpu["power"],
            }

    def start_slice(self, lbl: typing.Hashable) -> None:
        """Add a new named slice of activity.

        Parameters
        ----------
        lbl : hashable
            The section name, as a key of the final dictionay.
            If it is called several times, the slice with the same label are concatenated.

        Notes
        -----
        If this method is never called, the final result will not be pack into a dict.

        """
        assert hasattr(lbl, "__hash__"), lbl.__class__.__name__
        assert lbl is not None, "'None' is a forbidden label"
        if lbl in self._slices:
            msg = f"the method start_slice has already been called with the label {lbl!r}"
            raise KeyError(msg)
        # end last slice
        if self._slices_current_lbl is not None and self._slices[self._slices_current_lbl]:
            self._slices[self._slices_current_lbl][1] = (
                self._slices[self._slices_current_lbl][1] or time.time()
            )
        # start new slice
        self._slices[lbl] = [time.time(), None]
        self._slices_current_lbl = lbl

    def stop_slice(self) -> typing.Hashable:
        """Close the last slice.

        Returns
        -------
        lbl : hashable
            The name of the closed slice.

        """
        # check
        if self._slices_current_lbl is None:
            msg = "no slice capture in process"
            raise RuntimeError(msg)

        # end slice
        self._slices[self._slices_current_lbl][1] = time.time()

        # reset
        lbl = self._slices_current_lbl
        self._slices_current_lbl = None
        return lbl

    def _extract_slice(self, dt_lbl: str, data_lbls: list[str], start: float, stop: float) -> dict:
        """Extract data for the slice time.

        Paramaters
        ----------
        dt_lbl : str
            The label of the reference time durations.
        data_lbls : list[str]
            Labels of interset, to be cut.
        start, stop : float
            The absolute timestamps of the start and stop slice.

        Returns
        -------
        sub_slice : dict
            The cut and selected data.
            Only this labels and dt_lbl are in the final return dict.

        """
        assert isinstance(dt_lbl, str), dt_lbl.__class__.__name__
        assert dt_lbl in self.res, sorted(self.res)
        assert isinstance(data_lbls, list | tuple), data_lbls.__class__.__name__
        assert all(lbl in self.res for lbl in data_lbls), sorted(self.res)
        assert isinstance(start, float), start.__class__.__name__
        assert isinstance(stop, float), stop.__class__.__name__

        # get slice start and stop indicies
        dts = np.asarray(self.res[dt_lbl], dtype=np.float64)
        timestamps = self.res["start"] + dts.cumsum()
        timestamps = np.asarray([0.0, *timestamps.tolist(), np.inf], dtype=timestamps.dtype)
        idx_start = int((timestamps < start).view(np.uint8).argmin() - 1)
        idx_stop = int((timestamps >= stop).view(np.uint8).argmax())

        # restrict timestamps diff (dt) interval
        timestamps = timestamps[idx_start:idx_stop]
        timestamps[0], timestamps[-1] = start, stop

        # cut slices
        def cut_slice(data: list | dict, idx_start: int, idx_stop: int) -> list:
            """Select the slice."""
            match data:
                case list():
                    if not data:
                        return []
                    if isinstance(data[0], list | dict):
                        return [cut_slice(subdata, idx_start, idx_stop) for subdata in data]
                    if isinstance(data[0], numbers.Real):
                        return [data[0], *data, data[-1]][idx_start:idx_stop]
                    raise TypeError
                case dict():
                    return {
                        lbl: cut_slice(subdata, idx_start, idx_stop)
                        for lbl, subdata in data.items()
                    }
            raise TypeError

        return {
            **{lbl: cut_slice(self.res[lbl], idx_start, idx_stop) for lbl in data_lbls},
            dt_lbl: (timestamps[1:] - timestamps[:-1]).tolist(), # absolute to dt
        }

    def _trapez_integral_avg(self, times_delta: list[float], data: list | dict) -> float | dict:
        """Compute the average value of a data serie."""
        match data:
            case list() | tuple():
                if not data:
                    return np.nan
                if isinstance(data[0], list | tuple):  # shape (n_times_point, n_sensors)
                    return sum(self._trapez_integral_avg(times_delta, d) for d in zip(*data, strict=True))
                if isinstance(data[0], numbers.Real):
                    if duration := sum(times_delta):
                        if len(times_delta) == len(data):  # simple integral with rectangle
                            return sum(
                                dt * val for dt, val in zip(times_delta, data, strict=True)
                            ) / duration
                        if len(times_delta) == len(data) - 1:  # trapeze integration
                            return 0.5 * sum(  # trapeze integration
                                dt * (bmin + bmax)
                                for dt, bmin, bmax
                                in zip(times_delta, data[:-1], data[1:], strict=True)
                            ) / duration  # average of integral
                        msg = (
                            f"the dt length {len(times_delta)} "
                            f"and the data length {len(data)} are not compatible"
                        )
                        raise ValueError(msg)
                    else:
                        return np.nan
                raise TypeError
            case dict():
                return {k: self._trapez_integral_avg(times_delta, d) for k, d in data.items()}
        raise TypeError

    def __enter__(self) -> typing.Self:
        """Start to measure.

        Notes
        -----
        The returned dictionary is update inplace when we exit the code bloc.
        Only the successfull field are created.

        """
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        """Stop the measure and update the dictionary returnd by __enter__."""
        # stop
        self.res["duration"] = time.time() - self.res["start"]
        self._exit_queue.put(None)
        with contextlib.suppress(RuntimeError):
            self.stop_slice()
