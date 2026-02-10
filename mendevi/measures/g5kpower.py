"""Integrates grid5000's power meter.

Implementation based on https://www.grid5000.fr/w/Energy_consumption_monitoring_tutorial
"""

import datetime
import logging
import numbers
import re
import threading

import numpy as np
import requests

EPS = 1e-8
GOOD_REQ_STATUS = 200
MARGIN = 0.5  # request for thicker interval than requieres (in seconds)
PATTEREN_ISOTIME = r"^\d{2,4}-\d{1,2}-\d{1,2}\w\d\d:\d\d:(?P<sec>\d+\.\d*)(?:[+-]\d{1,2}:\d{1,2})?$"
SIMP_TOL = 1e-5


class G5kPower(threading.Thread):
    """Asynchronous consumption request on g5k."""

    def __init__(self, *args: tuple, **kwargs: dict) -> None:
        """Initialise the power thread."""
        super().__init__(daemon=True)
        self.args = args
        self.kwargs = kwargs
        self.power = None

    def run(self) -> None:
        """Perform the request."""
        try:
            self.power = g5kpower(*self.args, **self.kwargs)
        except ValueError as err:
            logging.getLogger(__name__).warning(err)

    def get(self) -> dict[str]:
        """Retrive the result."""
        self.join()
        return self.power


def g5kpower(
    hostname: str,
    start: numbers.Real,
    duration: numbers.Real,
    *,
    login: str | None = None,
    password: str | None = None,
) -> dict[str]:
    """Do a request to get the grid5000 consumption.

    Parameters
    ----------
    hostname : str
        The hostname containing the node name and the site.
        It can be get with `platform.node()`.
    start : float
        The starting timestamp, it can be get by `time.time()`.
    duration : float
        The job duration in seconds.
    login, password : str
        Username an password for grid5000 api.

    Returns
    -------
    Consumption: dict[str]
        * 'dt': The time difference between 2 consecutive power measurements (in s).
        * 'energy': The total energy consumption (in J).
        * 'power': The average power, energy divided by the duration (in w).
        * 'powers': The power measured between 2 consecutive points (in w).

    Raises
    ------
    ValueError
        If the request failed.

    Examples
    --------
    >>> import platform, time
    >>> from mendevi.measures.g5kpower import g5kpower
    >>> try:
    ...     power = g5kpower(platform.node(), time.time()-20.0, 10.0)
    ... except ValueError:
    ...     pass
    ...
    >>>

    Notes
    -----
    * Tested with `oarsub -I -p paradoxe -t deploy -t monitor='.*'`.
    * Power and time measurements are incremental to increase the compressibility
      of the database containing this result.
    * Energy is estimated from the trapezoidal integral of instantaneous powers.

    """
    # verification
    assert isinstance(hostname, str), hostname.__class__.__name__
    assert isinstance(start, numbers.Real), start.__class__.__name__
    assert isinstance(duration, numbers.Real), duration.__class__.__name__
    if (
        hostname_fields := re.search(
            r"^(?P<node>[a-z0-9_-]+)\.(?P<site>[a-z0-9_-]+)", hostname, re.IGNORECASE,
        )
    ) is None:
        msg = f"the hostname {hostname} is not grid5000 formated"
        raise ValueError(msg)

    def timestamp_to_str(timestamp: float) -> str:
        return datetime.datetime.fromtimestamp(  # noqa: DTZ006
            timestamp, tz=None,  # tz=datetime.UTC gives a shifted hour
        ).strftime("%Y-%m-%dT%H:%M:%S.%f")

    # grid5000 api request
    url = (  # tz=datetime.UTC add a non supported +00:00 by the g5k api
        f"https://api.grid5000.fr/stable/sites/{hostname_fields['site']}/metrics?"
        f"nodes={hostname_fields['node']}&metrics=wattmetre_power_watt,bmc_node_power_watt"
        f"&start_time={timestamp_to_str(start-MARGIN)}"
        f"&end_time={timestamp_to_str(start+duration+MARGIN)}"
    )
    # https://api.grid5000.fr/stable/sites/rennes/metrics?nodes=paradoxe-32&metrics=wattmetre_power_watt,bmc_node_power_watt&start_time=2026-02-02T08:47:51.889461&end_time=2026-02-02T08:48:01.889461
    auth = requests.auth.HTTPBasicAuth(login, password) if login and password else None
    try:
        req = requests.get(url, auth=auth, verify=True, timeout=60)
    except requests.exceptions.SSLError as err:
        logging.getLogger(__name__).info(err)
        req = requests.get(url, auth=auth, verify=False, timeout=60)
    if req.status_code != GOOD_REQ_STATUS:
        msg = f"the request {url} failed"
        raise ValueError(msg, req)
    if not (req := req.json()):
        msg = f"the request {url} gives an empty result"
        raise ValueError(msg)

    # parse result, req is formatted like that:
    # [{"timestamp":"2025...:00+02:00","metric_id":"wattmetre_power_watt","value":6.0526315...,...},
    #  {"timestamp":"2025...:00+02:00","metric_id":"wattmetre_power_watt","value":6.3324324324,...},
    #  {"timestamp":"2025...:00.654002+02:00","metric_id":"bmc_node_power_watt","value":0,...},
    #  {"timestamp":"2025...:00.654322+02:00","metric_id":"bmc_node_power_watt","value":0,...},
    #  {"timestamp":"2025...:01+02:00","metric_id":"wattmetre_power_watt","value":6.0707317073,...},
    #  {"timestamp":"2025...:01+02:00","metric_id":"wattmetre_power_watt","value":6.2390243902,...},
    # ...

    # 2026-03-02T15:16:17.6542165413521+/-01:00

    def to_iso(date: str) -> str:
        """Convert iso for retrocompatibility python < 3.11.

        Set the norm: YYYY-MM-DD[*HH[:MM[:SS[.fff[fff]]]][+HH:MM[:SS[.ffffff]]]]
        """
        if (match := re.search(PATTEREN_ISOTIME, date)) is None:
            logging.getLogger(__name__).error("failed to convert %s", date)
            return date
        return date.replace(match["sec"], f"{float(match['sec']):.6f}")

    req = [
        {
            "timestamp": datetime.datetime.fromisoformat(to_iso(data["timestamp"])).timestamp(),
            "metric_id": data["metric_id"],
            "value": data["value"],
        }
        for data in req
    ]
    req = {
        "wattmetre_power_watt": {
            d["timestamp"]: d["value"] for d in req if d["metric_id"] == "wattmetre_power_watt"
        },
        "bmc_node_power_watt": {
            d["timestamp"]: d["value"] for d in req if d["metric_id"] == "bmc_node_power_watt"
        },
    }
    req = req["wattmetre_power_watt"] or req["bmc_node_power_watt"]
    times, powers = zip(*req.items(), strict=False)
    times, powers = np.array(times, dtype=np.float64), np.array(powers, dtype=np.float64)

    # pad for accurate boundaries
    order = np.argsort(times)
    times, powers = times[order], powers[order]
    times = times.clip(start, start+duration, out=times)  # if timestamp out of the bounds
    times = np.concatenate([(start,), times, (start+duration,)])  # edge padding, cst interpolation
    powers = np.concatenate([(powers[0],), powers, (powers[-1],)])

    # compute energy, trapeze integral of power
    power_dt = times[1:] - times[:-1]
    energy = 0.5 * float(np.sum((powers[:-1] + powers[1:]) * power_dt))

    return {
        "dt": power_dt.tolist(),
        "energy": energy,
        "power": energy / duration,
        "powers": powers.tolist(),
    }
