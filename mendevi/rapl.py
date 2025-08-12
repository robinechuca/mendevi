#!/usr/bin/env python3

"""Try to read the energy with RAPL."""

import logging
import numbers
import os
import re
import subprocess
import sys
import time


PATTERN = re.compile(br"^(?P<time>\d+\.\d*);(?P<energy>\d+[.,]\d*);(?P<unit>Joules)")


class RAPL:
    """Uses the linux perf command through a python context manager.

    Examples
    --------
    >>> import time
    >>> from mendevi.rapl import RAPL
    >>> with RAPL() as energy:
    ...     time.sleep(1)
    ...
    >>>
    """

    def __init__(self, sleep: numbers.Real=50e-3, no_fail: bool=False):
        """Initalize the perf context.

        Parameters
        ----------
        sleep : float, default=50e-3
            The time interval between 2 measures (in s).
        no_fail : bool, default=True
            If False, raise RuntimeError if it fails to get the RAPL measure.
            Otherwise (if True), return None instead of failing.
        """
        assert isinstance(sleep, numbers.Real), sleep.__class__.__name__
        assert sleep > 0, sleep
        assert isinstance(no_fail, bool), no_fail

        self.sleep = round(1000*float(sleep))
        self.res: dict = {"dt": [], "energy": None, "power": None, "powers": []}
        self.process = subprocess.Popen(  # pylint: disable=R1732
            [  # sudo apt install linux-perf
                "perf", "stat",
                "--event", "power/energy-pkg/",  # cores and cache, no ram
                "--all-cpus",
                "--field-separator", ";",  # output csv like
                "--interval-print", str(self.sleep),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.lines = [self.process.stderr.readline()]
        self.time_bounds = [time.time(), None, None]  # start proc, measure, stop
        if PATTERN.search(self.lines[0]) is None:
            if os.geteuid() != 0:  # if not root
                logging.error("try with 'sudo %s'", sys.executable)
                logging.error("or give rights with sudo sysctl -w kernel.perf_event_paranoid=0")
            self.lines.extend(self.process.stderr.readlines())
            if not no_fail:
                raise RuntimeError(b"".join(self.lines).decode())
            logging.error(b"".join(self.lines).decode())
            self.res = None

    def __enter__(self) -> dict:
        """Start to measure.

        Returns
        -------
        Consumption: dict[str]
            * 'dt': The time difference between 2 consecutive power measurements (in s).
            * 'energy': The total energy consumption (in J).
            * 'power': The average power, energy divided by the duration (in w).
            * 'powers': The power measured between 2 consecutive points (in w).
        """
        self.time_bounds[1] = time.time()
        return self.res

    def __exit__(self, *_):
        """Stop the measure and update the dictionary returnd by __enter__."""
        # stop measuring
        self.time_bounds[2] = time.time()
        time.sleep(self.sleep/1000)  # to be shure catching the last point
        self.process.terminate()
        self.lines.extend(self.process.stderr.readlines())

        # exit if failed
        if self.res is None:
            return

        # decode output
        values = [PATTERN.search(l) for l in self.lines]
        times_end, energy = zip(
            *(
                (float(p["time"]), float(p["energy"].replace(b",", b".")))
                for p in values if p is not None
            )
        )

        # convert energy in power
        times_end = [t - times_end[0] + self.time_bounds[0] for t in times_end]
        times_start = [times_end[0] - self.sleep/1000] + times_end[:-1]
        powers = [e / (te - ts) for e, ts, te in zip(energy, times_start, times_end)]

        # pad and crop
        while times_end[-1] < self.time_bounds[2]:  # pad
            times_end.append(times_end[-1] + self.sleep/1000)
            times_start.append(times_end[-2])
            powers.append(powers[-1])  # assumption: cst interpolation
        while times_end[0] < self.time_bounds[1]:  # crop start
            del times_start[0], times_end[0], powers[0]
        while times_start[-1] > self.time_bounds[2]:  # crop end
            del times_start[-1], times_end[-1], powers[-1]
        times_start[0], times_end[-1] = self.time_bounds[1], self.time_bounds[2]

        # compute total energy
        self.res["dt"] = [te - ts for ts, te in zip(times_start, times_end)]
        self.res["energy"] = sum(p * dt for p, dt in zip(powers, self.res["dt"]))
        self.res["power"] = self.res["energy"] / (times_end[-1] - times_start[0])
        self.res["powers"] = powers
