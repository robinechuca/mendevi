"""Query the GPUs activity."""

import numbers
import threading
import time

import numpy as np
import pynvml  # uv pip install nvidia-ml-py

# initialisation
try:
    pynvml.nvmlInit()
except pynvml.NVMLError:
    GPUS = 0
else:
    GPUS: int = pynvml.nvmlDeviceGetCount()


def measure() -> dict[str]:
    """Get a instantaneous capture of all gpus."""
    memory, gpus, powers = [], [], []
    for i in range(GPUS):
        hand = pynvml.nvmlDeviceGetHandleByIndex(i)
        powers.append(pynvml.nvmlDeviceGetPowerUsage(hand) / 1000.0)  # in Watts
        gpus.append(pynvml.nvmlDeviceGetUtilizationRates(hand).gpu / 100.0)  # in [0, 1]
        memory.append(pynvml.nvmlDeviceGetMemoryInfo(hand).used)  # in bytes
    return {"memory": memory, "gpus": gpus, "powers": powers}


class UsageGPU(threading.Thread):
    """Use pynvml through a python context manager.

    Examples
    --------
    >>> import time
    >>> from mendevi.measures.gpu import UsageGPU
    >>> with UsageGPU() as gpu:
    ...     time.sleep(1)
    ...
    >>>

    """

    def __init__(self, sleep: numbers.Real = 50e-3) -> None:
        """Initialize the usage context.

        Parameters
        ----------
        sleep : float, default=50e-3
            The time interval between 2 measures (in s).

        """
        super().__init__(daemon=True)

        assert isinstance(sleep, numbers.Real), sleep.__class__.__name__
        assert sleep > 0, sleep

        self._stop_flag = False
        self.sleep = float(sleep)
        self.res: dict | None = {
            "dt": [],
            "energy": None,
            "gpus": [],
            "memory": [],
            "power": None,
            "powers": [],
        } if GPUS else None

    def run(self) -> None:
        """Perform the measures."""
        while GPUS and not self._stop_flag:
            t_init = time.time()
            for cat, vals in measure().items():
                self.res[cat].append(vals)
            time.sleep(max(0.0, self.sleep + t_init - time.time()))
            self.res["dt"].append(time.time() - t_init)

    def __enter__(self) -> dict:
        """Start to measure.

        Returns
        -------
        Consumption: dict[str]
            * 'dt': The time difference between 2 consecutive power measurements (in s).
            * 'energy': The total energy consumption (in J).
            * 'gpus': The mean usage of all the logical gpus.
            * 'memory': The memory used for each gpu (in bytes).
            * 'power': The average power, energy divided by the duration (in w).
            * 'powers': The power measured between 2 consecutive points (in w).

        """
        self.start()
        return self.res

    def __exit__(self, *_: object) -> None:
        """Stop the measure and update the dictionary returnd by __enter__."""
        self._stop_flag = True
        self.join()  # wait the last update of self.run
        if GPUS:
            self.res["gpu"] = float(np.mean(self.res["gpus"], axis=0).sum())

            # compute total energy
            self.res["energy"] = sum(
                sum(ps) * dt for ps, dt in zip(self.res["powers"], self.res["dt"], strict=False)
            )
            self.res["power"] = self.res["energy"] / sum(self.res["dt"])
