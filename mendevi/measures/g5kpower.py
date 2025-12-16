"""Integrates grid5000's power meter."""

import datetime
import logging
import numbers
import re
import threading

import numpy as np
import requests

GOOD_REQ_STATUS = 200


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
    ...     power = g5kpower(platform.node(), time.time()-10.0, 10.0)
    ... except ValueError:
    ...     pass
    ...
    >>>

    Notes
    -----
    * Tested with `oarsub -I -p paradoxe -t deploy -t monitor='wattmetre_power_watt'`.
    * Power and time measurements are differental to increase the compressibility
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
        return datetime.datetime.fromtimestamp(
            timestamp, tz=datetime.UTC,
        ).strftime("%Y-%m-%dT%H:%M:%S.%f")

    # grid5000 api request
    url = (  # tz=datetime.UTC add a non supported +00:00 by the g5k api
        f"https://api.grid5000.fr/stable/sites/{hostname_fields['site']}/metrics?"
        f"nodes={hostname_fields['node']}&metrics=wattmetre_power_watt"
        f"&start_time={timestamp_to_str(start)}"
        f"&end_time={timestamp_to_str(start+duration)}"
    )
    auth = requests.auth.HTTPBasicAuth(login, password) if login and password else None
    try:
        req = requests.get(url, auth=auth, verify=True, timeout=60)
    except requests.exceptions.SSLError as err:
        logging.getLogger(__name__).warning(err)
        req = requests.get(url, auth=auth, verify=False, timeout=60)
    if req.status_code != GOOD_REQ_STATUS:
        msg = f"the request {url} failed"
        raise ValueError(msg, req)
    if not (req := req.json()):
        msg = f"the request {url} gives an empty result"
        raise ValueError(msg)

    # parse result
    req = {datetime.datetime.fromisoformat(d["timestamp"]).timestamp(): d["value"] for d in req}
    req = {t: v for t, v in req.items() if start <= t <= start + duration}
    times, powers = zip(*req.items(), strict=False)
    times, powers = np.array(times, dtype=np.float64), np.array(powers, dtype=np.float64)

    # pad for accurate boundaries
    order = np.argsort(times)
    times, powers = times[order], powers[order]
    times = np.concatenate([(start,), times, (start+duration,)])  # accurate boundaries
    powers = np.pad(powers, (1, 1), mode="edge")

    # differencial
    power_dt = times[1:] - times[:-1]

    # compute energy, trapeze integral of power
    energy = 0.5 * float(np.sum((powers[:-1] + powers[1:]) * power_dt))

    return {
        "dt": power_dt.tolist(),
        "energy": energy,
        "power": energy / float(times[-1] - times[0]),
        "powers": powers.tolist(),
    }
