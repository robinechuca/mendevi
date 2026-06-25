"""Query the GPUs activity."""

import numbers
import queue
import threading
import time

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
    memory, gpu, power = [], [], []
    for i in range(GPUS):
        hand = pynvml.nvmlDeviceGetHandleByIndex(i)
        power.append(pynvml.nvmlDeviceGetPowerUsage(hand) / 1000.0)  # in Watts
        gpu.append(pynvml.nvmlDeviceGetUtilizationRates(hand).gpu / 100.0)  # in [0, 1]
        memory.append(pynvml.nvmlDeviceGetMemoryInfo(hand).used)  # in bytes
    return {"memory": memory, "gpu": gpu, "power": power}


class UsageGPU(threading.Thread):
    """Use pynvml through a python context manager.

    Examples
    --------
    >>> from mendevi.measures.gpu import UsageGPU
    >>> with UsageGPU() as gpu:
    ...     pass
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

        self._signal_queue = queue.Queue()
        self._stop_flag = False
        self.sleep = float(sleep)
        self.res: dict | None = {
            "ts": [],
            "gpu": [],
            "memory": [],
            "power": [],
        } if GPUS else None

    def run(self) -> None:
        """Perform the measures."""
        is_warming = True
        if self.res is None:
            self._signal_queue.put(None)
            return
        # reset the measures
        for data in self.res.values():
            data.clear()

        # start measurements
        self.res["ts"].append(time.time())
        try:
            while True:
                for cat, vals in measure().items():
                    self.res[cat].append(vals)
                if is_warming:
                    is_warming = False
                    self._signal_queue.put(None)  # send signal catched by .__enter__()
                time.sleep(max(0.0, self.sleep + self.res["ts"][-1] - time.time()))
                self.res["ts"].append(time.time())
                if self._stop_flag:
                    break
        except Exception as err:
            self._signal_queue.put(err)
            raise

    def __enter__(self) -> dict:
        """Start to measure.

        Returns
        -------
        Consumption: dict[str]
            * 'gpu': The mean usage of all the logical gpus. Shape (n_points, n_gpu).
            * 'memory': The memory used for each gpu (in bytes). Shape (n_points, n_gpu).
            * 'power': The power measured between 2 consecutive points (in w). (n_points, n_gpu).
            * 'ts': The time duration of each measurements (in s). Shape (n_points+1,).

        """
        self.start()
        if (err := self._signal_queue.get()) is not None:  # wait until the first frame is catched
            raise err
        return self.res

    def __exit__(self, *_: object) -> None:
        """Stop the measure and update the dictionary returnd by __enter__."""
        self._stop_flag = True
        self.join()  # wait the last update of self.run
        try:
            err = self._signal_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            raise err
