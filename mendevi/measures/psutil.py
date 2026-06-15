"""Use psutil to record the CPU and RAM usage."""

import numbers
import queue
import threading
import time

import psutil


class Usage(threading.Thread):
    """Use psutil through a python context manager.

    Examples
    --------
    >>> from mendevi.measures.psutil import Usage
    >>> with Usage() as usage:
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
        self.res: dict = {"ts": [], "cpu": [], "ram": [], "temp": {}}

    def run(self) -> None:
        """Perform the measures."""
        is_warming = True
        # reset the measures
        for data in self.res.values():
            data.clear()
        self.res["ts"].append(time.time())
        while True:
            self.res["cpu"].append(psutil.cpu_percent(self.sleep, percpu=True))
            self.res["ram"].append(psutil.virtual_memory().used)
            temp: dict[str, float] = {
                f"{generic}_{shwtemp.label or i}": shwtemp.current
                for generic, shwtemps in psutil.sensors_temperatures().items()
                for i, shwtemp in enumerate(shwtemps)
            }
            for lbl, degrees in temp.items():
                self.res["temp"][lbl] = self.res["temp"].get(lbl, [])
                self.res["temp"][lbl].append(degrees)
            self.res["ts"].append(time.time())
            # sometimes, temperature data is missing
            # so we duplicate the missing temperature to ensure the data len is complete
            for lbl in self.res["temp"]:
                while len(self.res["temp"][lbl]) < len(self.res["ts"]) - 1:
                    self.res["temp"][lbl].append(self.res["temp"][lbl][-1])
            # send signal
            if is_warming:
                is_warming = False
                self._signal_queue.put(None)  # send signal catched by .__enter__()
            # exit
            if self._stop_flag:
                break


    def __enter__(self) -> dict:
        """Start to measure.

        Returns
        -------
        Consumption: dict[str]
            * 'cpu': Each logical cpu usage at each time (in %). Shape (n_points, n_cpu).
            * 'ram': The virtual ram usage (in bytes). Shape (n_points,).
            * 'temp': The temperatures measured at each moment for all sensors (in C).
            * 'ts': The time duration of each measurements (in s). Shape (n_points+1,).

        """
        self.start()
        self._signal_queue.get()  # wait until the first frame is catched
        return self.res

    def __exit__(self, *_: object) -> None:
        """Stop the measure and update the dictionary returnd by __enter__."""
        self._stop_flag = True
        self.join()  # wait the last update of self.run
