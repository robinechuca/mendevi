#!/usr/bin/env python3

"""All measurement helper."""

import numbers
import platform
import queue
import threading
import time

from .g5kpower import g5kpower
from .gpu import UsageGPU
from .psutil import Usage
from .rapl import RAPL

G5K_API_WAIT = 2.0  # waiting time (in seconds) before data from the grid5000 API becomes accessible


class Activity(threading.Thread):
    """Measure the computer activity of a section.

    Examples
    --------
    >>> import pprint, time
    >>> from mendevi.measures import Activity
    >>> with Activity() as activity:
    ...     time.sleep(1)
    ...
    >>> pprint.pprint(activity)
    >>>

    """

    def __init__(self, sleep: numbers.Real = 50e-3):
        """Init the perf context.

        Parameters
        ----------
        sleep : float, default=50e-3
            The time interval between 2 measures (in s).

        """
        assert isinstance(sleep, numbers.Real), sleep.__class__.__name__
        assert sleep > 0, sleep

        super().__init__(daemon=True)

        self._rapl_catcher = RAPL(sleep=sleep, no_fail=True)
        self._usage_catcher = Usage(sleep=sleep)
        self._usage_gpu_catcher = UsageGPU(sleep=sleep)
        self._exit_queue = queue.Queue()
        self.sleep = float(sleep)
        self.res: dict = {}

    def run(self):
        """Perform the measures."""
        self.res["start"] = time.time()
        with (
            self._rapl_catcher as rapl,
            self._usage_catcher as usage,
            self._usage_gpu_catcher as gpu,
        ):
            self._exit_queue.get()  # wait
        self.res |= {
            "ps_core": usage["cpu"],
            "ps_cores": usage["cpus"],
            "ps_dt": usage["dt"],
            "ps_ram": usage["ram"],
        }
        if rapl is not None:
            self.res |= {
                "rapl_dt": rapl["dt"],
                "rapl_energy": rapl["energy"],
                "rapl_power": rapl["power"],
                "rapl_powers": rapl["powers"],
            }
        if gpu is not None:
            self.res |= {
                "gpu_cores": gpu["gpus"],
                "gpu_dt": gpu["dt"],
                "gpu_energy": gpu["energy"],
                "gpu_memory": gpu["memory"],
                "gpu_power": gpu["power"],
                "gpu_powers": gpu["powers"],
            }

    def __enter__(self) -> dict:
        r"""Start to measure.

        Returns
        -------
        activity: dict[str]
            * duration: float, the real measure duration.
            * ps_core: float, the mean cummulated usage of all the logical cpus.
            * ps_cores: list[list[float]], tensor of detailed usage of each logical core in %.
            * ps_dt: list[float], the duration of each interval (in s).
            * ps_ram: list[int], list of the sampled ram usage in bytes in each point.
            * rapl_dt: list[float], the duration of each interval (in s).
            * rapl_energy: float, the total energy consumption (in J).
            * rapl_power: float, the average power, energy divided by the duration (in w).
            * rapl_powers: list[float], the average power in watt in each interval.
            * start: float, absolute timestamp.
            * wattmeter_dt: list[float], the duration of each interval (in s).
            * wattmeter_energy: float, the total energy consumption (in J).
            * wattmeter_power: float, the average power, energy divided by the duration (in w).
            * wattmeter_powers: list[float], the sampled power in watt in each point.

        Notes
        -----
        The returned dictionary is update inplace when we exit the code bloc.
        Only the successfull field are created.

        """
        self.start()
        return self.res

    def __exit__(self, *_):
        """Stop the measure and update the dictionary returnd by __enter__."""
        # stop
        self.res["duration"] = time.time() - self.res["start"]
        self._exit_queue.put(None)
        self.join()
        # request wattmeter power
        time.sleep(max(0.0, G5K_API_WAIT + self.res["start"] + self.res["duration"] - time.time()))
        try:
            wattmeter = g5kpower(platform.node(), self.res["start"], self.res["duration"])
        except ValueError:
            wattmeter = None
        else:
            self.res |= {
                "wattmeter_dt": wattmeter["dt"],
                "wattmeter_energy": wattmeter["energy"],
                "wattmeter_power": wattmeter["power"],
                "wattmeter_powers": wattmeter["powers"],
            }
