#!/usr/bin/env python3

"""Use psutil to record the CPU and RAM usage."""

import numbers
import threading
import time

import numpy as np
import psutil


class Usage(threading.Thread):
    """Use psutil through a python context manager.

    Examples
    --------
    >>> import time
    >>> from mendevi.usage import Usage
    >>> with Usage() as usage:
    ...     time.sleep(1)
    ...
    >>>
    """

    def __init__(self, sleep: numbers.Real=50e-3):
        """Initialize the usage context.

        Paremeters
        ----------
        sleep : float, default=50e-3
            The time interval between 2 measures (in s).
        """
        super().__init__(daemon=True)

        assert isinstance(sleep, numbers.Real), sleep.__class__.__name__
        assert sleep > 0, sleep

        self._stop = False
        self.sleep = float(sleep)
        self.res: dict = {"dt": [], "avg_cpu": None, "cpu": [], "ram": []}

    def run(self):
        """Perform the measures."""
        while not self._stop:
            t_init = time.time()
            self.res["cpu"].append(psutil.cpu_percent(self.sleep, percpu=True))
            self.res["ram"].append(psutil.virtual_memory().used)
            self.res["dt"].append(time.time() - t_init)

    def __enter__(self) -> dict:
        """Start to measure.

        Returns
        -------
        Consumption: dict[str]
            * 'dt': The time difference between 2 consecutive measurements (in s).
            * 'thread': The mean cummulated usage of all the logical cpus.
            * 'cpu': The cpu usage for each thread (in %).
            * 'ram': The virtual ram usage (in bytes).
        """
        self.start()
        return self.res

    def __exit__(self, *_):
        """Stop the measure and update the dictionary returnd by __enter__."""
        self._stop = True
        self.join()  # wait the last update of self.run
        self.res["thread"] = psutil.cpu_count() * float(np.mean(self.res["cpu"])) / 100.0
