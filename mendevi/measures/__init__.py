# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

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
from .g5kpower import MARGIN, g5kpower
from .gpu import UsageGPU
from .psutil import Usage
from .rapl import RAPL

G5K_API_WAIT = 5.0 + MARGIN  # waiting time (in s) before data from the g5k API becomes accessible


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
    >>> slices = activity.get_slices()
    >>> sorted(slices)
    ['lbl 1', 'lbl 2', 'lbl 3']
    >>> round(sum(s["duration"] for s in slices.values()), 2)
    0.9
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
        self._exit_queue, self._started_queue = queue.Queue(), queue.Queue()
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
            * gpu_memory: list[list[float]], tensor of the memory usage of each GPU in bytes.
            * gpu_memory_avg: float, the sum of the average memory usage of each GPU.
            * gpu_power: list[list[float]], the sampled power in each point (in W).
            * gpu_power_avg: float, the total power consumption of all GPU (in W).
            * ps_core: list[list[float]], tensor of detailed usage of each logical core in %.
            * ps_core_avg: float, the mean cumulative usage of all the logical cpus.
            * ps_dt: list[float], the duration of each interval (in s).
            * ps_ram: list[int], list of the sampled ram usage in bytes in each point.
            * ps_ram_avg: float, the average ram usage in bytes in each point.
            * ps_temp: dict[str, list[float]], the temperature of each device (in C).
            * ps_temp_avg: dict[str, float], the average temperature of each device (in C).
            * rapl_dt: list[float], the duration of each interval (in s).
            * rapl_power: list[float], the average power in each interval (in W).
            * rapl_power_avg: float, the average power, energy divided by the duration (in W).
            * start: float, absolute timestamp.
            * wattmeter_dt: list[float], the duration of each interval (in s).
            * wattmeter_power: list[float], the sampled power in watt in each point.
            * wattmeter_power_avg: float, the average power, energy divided by the duration (in W).

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
        if "wattmeter_ts" not in self.res:  # ADEC and GRID'5000 are mutually exclusive
            time.sleep(max(
                0.0,
                G5K_API_WAIT + self.res["start"] + self.res["duration"] - time.time(),
            ))
            try:
                wattmeter = g5kpower(platform.node(), self.res["start"], self.res["duration"])
            except ValueError:
                pass
            else:
                self.res |= {
                    "wattmeter_ts": wattmeter[0],
                    "wattmeter_power": wattmeter[1],
                }
        # cut slices
        tslbl_datalbls = (
            ("ps_ts", ("ps_core", "ps_ram", "ps_temp")),
            ("rapl_ts", ("rapl_power",)),
            ("gpu_ts", ("gpu_core", "gpu_memory", "gpu_power")),
            ("wattmeter_ts", ("wattmeter_power",)),
        )
        tslbl_datalbls = tuple((ts, fields) for ts, fields in tslbl_datalbls if ts in self.res)
        if self._slices:
            slices = {  # each slice, not concats
                slicelbl: {
                    **{
                        fieldlbl: data
                        for ts_lbl, data_lbls in tslbl_datalbls
                        for fieldlbl, data in self._extract_slice(
                            ts_lbl, data_lbls, start, stop,
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
                        f"{f_lbl}_avg": self._integral_avg(
                            data[f"{ts_lbl[:-2]}dt"], data[f_lbl],
                        )
                        for ts_lbl, fieldlbls in tslbl_datalbls for f_lbl in fieldlbls
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
        with (
            self._adec_catcher as adec,
            self._rapl_catcher as rapl,
            self._usage_catcher as usage,
            self._usage_gpu_catcher as gpu,
        ):
            self.res["start"] = time.time() # as close as possible to the exit of __enter__
            self._started_queue.put(None)  # send signal catched by .__enter__()
            self._exit_queue.get()  # wait the signal sent by .__exit__()
        self.res |= {
            "ps_core": usage["cpu"],
            "ps_ts": usage["ts"],
            "ps_ram": usage["ram"],
            "ps_temp": usage["temp"],
        }
        if adec is not None:
            self.res |= {
                "wattmeter_ts": adec["ts"],
                "wattmeter_power": [sum(p) for p in adec["p_eff"]],
            }
        if rapl is not None:
            self.res |= {
                "rapl_ts": rapl["ts"],
                "rapl_power": rapl["power"],
            }
        if gpu is not None:
            self.res |= {
                "gpu_ts": gpu["ts"],
                "gpu_core": gpu["gpu"],
                "gpu_memory": gpu["memory"],
                "gpu_power": gpu["power"],
            }

    def start_slice(self, lbl: typing.Hashable) -> None:
        """Add a new named slice of activity.

        Parameters
        ----------
        lbl : hashable
            The section name, as a key of the final dictionary.
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

    def _extract_slice(self, ts_lbl: str, data_lbls: list[str], start: float, stop: float) -> dict:
        """Extract data for the slice time.

        Paramaters
        ----------
        ts_lbl : str
            The label of the reference timestamps boundaries.
        data_lbls : list[str]
            Labels of interset, to be cut.
        start, stop : float
            The absolute timestamps of the start and stop slice.

        Returns
        -------
        sub_slice : dict
            The cut and selected data.
            Only this labels and ts_lbl are in the final return dict.

        """
        assert isinstance(ts_lbl, str), ts_lbl.__class__.__name__
        assert ts_lbl in self.res, sorted(self.res)
        assert isinstance(data_lbls, list | tuple), data_lbls.__class__.__name__
        assert all(lbl in self.res for lbl in data_lbls), sorted(self.res)
        assert isinstance(start, float), start.__class__.__name__
        assert isinstance(stop, float), stop.__class__.__name__

        # get slice start and stop indicies
        timestamps = np.asarray([0.0, *self.res[ts_lbl], np.inf], dtype=np.float64)
        idx_start = int((timestamps <= start).view(np.uint8).argmin() - 1)
        idx_stop = int((timestamps >= stop).view(np.uint8).argmax())

        # restrict timestamps diff (dt) interval
        timestamps = timestamps[idx_start:idx_stop+1]
        timestamps[0], timestamps[-1] = start, stop

        # cut slices
        def cut_slice(data: list | dict, idx_start: int, idx_stop: int) -> list:
            """Select the slice."""
            match data:
                case list() | tuple():
                    if not data:
                        return []
                    if isinstance(data[0], list | tuple):  # shape (n_times_point, n_sensors)
                        return list(zip(
                            *(
                                cut_slice(subdata, idx_start, idx_stop)
                                for subdata in zip(*data, strict=True)
                            ),
                            strict=True,
                        ))
                        # return [cut_slice(subdata, idx_start, idx_stop) for subdata in data]
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
            f"{ts_lbl[:-2]}dt": (timestamps[1:] - timestamps[:-1]).tolist(),  # ts to dt
        }

    def _integral_avg(self, times_delta: list[float], data: list | dict) -> float | dict:
        """Compute the average value of a data serie."""
        match data:
            case list() | tuple():
                if not data:
                    return np.nan
                if isinstance(data[0], list | tuple):  # shape (n_times_point, n_sensors)
                    return sum(
                        self._integral_avg(times_delta, d) for d in zip(*data, strict=True)
                    )
                if isinstance(data[0], numbers.Real):
                    if len(times_delta) != len(data):
                        msg = (
                            f"the dt length {len(times_delta)} "
                            f"and the data length {len(data)} are not compatible"
                        )
                        raise ValueError(msg)
                    return sum(   # simple integral with rectangle
                        dt * val for dt, val in zip(times_delta, data, strict=True)
                    ) / sum(times_delta)
                raise TypeError
            case dict():
                return {k: self._integral_avg(times_delta, d) for k, d in data.items()}
        raise TypeError

    def __enter__(self) -> typing.Self:
        """Start to measure."""
        self.start()
        self._started_queue.get()  # wait until the acquisitions are well established
        return self

    def __exit__(self, *_: object) -> None:
        """Stop the measure and update the dictionary returnd by __enter__."""
        # stop
        self.res["duration"] = time.time() - self.res["start"]
        self._exit_queue.put(None)  # send a signal catched by .run()
        with contextlib.suppress(RuntimeError):
            self.stop_slice()
