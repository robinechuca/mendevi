"""Power prediction based on CPU utilisation rate."""

import logging
import math

import numpy as np
from context_verbose import Printer

from mendevi.models import Model

MIN_POINTS = 2  # minimal number of points


class PowerCores(Model):
    r"""Affine model to predict the power from the core utilisation.

    .. math:

        P(c) = P_{static} + c \times P_{core}

    With :math:`P_{static}` and :math:`P_{core}`
    two hyperparameters specific to each machine,
    but independent of the programme being executed.

    Examples
    --------
    >>> from mendevi.models.power_cores import PowerCores
    >>> model = PowerCores()
    >>> model.fit("<multithread.db>")
    >>> model.predict(["paradoxe-32.rennes.grid5000.fr"], [0.0])
    >>>

    """

    def __init__(self) -> None:
        """Initialise the model."""
        super().__init__(
            "Power estimation based on the utilisation rate of logic cores",
            sources="""
            F. C. Heinrich, T. Cornebize, A. Degomme, A. Legrand, A. Carpen-
            Amarie, S. Hunold, A.-C. Orgerie, and M. Quinson, “Predicting the
            Energy Consumption of MPI Applications at Scale Using a Single
            Node,” in IEEE Cluster Conference, 2017.

            R. Rodriguez-Sánchez, F. D. Igual, J. L. Martinez, R. Mayo, and E. S.
            Quintana-Orti, “Parallel performance and energy efficiency of modern
            video encoders on multithreaded architectures,” in Eur
            """,
            input_labels=["hostname", "cores"],
            output_labels=["power"],
            parameters={},  # to each hostname, associate P_{static} and P_{core}
        )

    def _fit(self, values: dict[str]) -> None:
        """Perform a linear regression for the 2 constants P_{static} and P_{core}."""
        for hostname in set(values["hostname"]):
            with Printer(f"Affine regression of power = f(cores) on {hostname}...") as prt:
                mask = [i for i, h in enumerate(values["hostname"]) if h == hostname]
                prt.print(f"fit on {len(mask)} points")
                if len(mask) < MIN_POINTS:
                    logging.getLogger(__name__).error(
                        "can not fit model for hostname=%s, not enouth points", hostname,
                    )
                    continue
                cores = [values["cores"][i] for i in mask]
                power = [values["power"][i] for i in mask]
                p_cores, p_static = np.polyfit(cores, power, deg=1)
                prt.print(f"power = {p_static:.3g} + cores * {p_cores:.3g}")
                self.parameters[hostname] = {"p_static": float(p_static), "p_cores": float(p_cores)}

    def _predict(self, values: dict[str]) -> dict[str]:
        all_power = []
        for hostname, cores in zip(values["hostname"], values["cores"], strict=True):
            if hostname not in self.parameters:
                logging.getLogger(__name__).error(
                    "fit the model for the hostname %s before to predict", hostname,
                )
                all_power.append(math.nan)
            else:
                all_power.append(
                    self.parameters[hostname]["p_static"]
                    + cores * self.parameters[hostname]["p_cores"],
                )
        return {"power": all_power}
