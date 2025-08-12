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
    >>> from mendevi.psutil import Usage
    >>> with Usage() as usage:
    ...     time.sleep(1)
    ...
    >>>
    """

    def __init__(self, sleep: numbers.Real=50e-3):
        """Initialize the usage context.

        Parameters
        ----------
        sleep : float, default=50e-3
            The time interval between 2 measures (in s).
        """
        super().__init__(daemon=True)

        assert isinstance(sleep, numbers.Real), sleep.__class__.__name__
        assert sleep > 0, sleep

        self._stop = False
        self.sleep = float(sleep)
        self.res: dict = {"dt": [], "pcu": None, "cpus": [], "ram": []}

    def run(self):
        """Perform the measures."""
        while not self._stop:
            t_init = time.time()
            self.res["cpus"].append(psutil.cpu_percent(self.sleep, percpu=True))
            self.res["ram"].append(psutil.virtual_memory().used)
            self.res["dt"].append(time.time() - t_init)

    def __enter__(self) -> dict:
        """Start to measure.

        Returns
        -------
        Consumption: dict[str]
            * 'cpu': The mean cummulated usage of all the logical cpus.
            * 'cpus': Each logical cpu usage at each time (in %).
            * 'dt': The time difference between 2 consecutive measurements (in s).
            * 'ram': The virtual ram usage (in bytes).
        """
        self.start()
        return self.res

    def __exit__(self, *_):
        """Stop the measure and update the dictionary returnd by __enter__."""
        self._stop = True
        self.join()  # wait the last update of self.run
        self.res["cpu"] = float(np.mean(self.res["cpus"], axis=0).sum())
