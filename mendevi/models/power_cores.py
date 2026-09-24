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
    >>> model = PowerCores().fit("<multithread.db>")
    >>> model.predict(["paradoxe-32.rennes.grid5000.fr"], [0.0])
    {'power': [247.53499079469898]}
    >>>

    """

    def __init__(self) -> None:
        """Initialise the model."""
        super().__init__(
            "Power estimation based on the utilisation rate of logic cores",
            sources="""
            F. C. Heinrich, T. Cornebize, A. Degomme, A. Legrand, A. Carpen-
            Amarie, S. Hunold, A.-C. Orgerie, and M. Quinson, "Predicting the
            Energy Consumption of MPI Applications at Scale Using a Single
            Node," in IEEE Cluster Conference, 2017.

            R. Rodriguez-Sánchez, F. D. Igual, J. L. Martinez, R. Mayo, and E. S.
            Quintana-Orti, "Parallel performance and energy efficiency of modern
            video encoders on multithreaded architectures," in Eur
            """,
            input_labels=["hostname", "cores"],
            output_labels=["power"],
        )

    def _fit(self, values: dict[str]) -> object:
        """Perform a linear regression for the 2 constants P_{static} and P_{core}."""
        with Printer(f"Affine regression of power = f(cores)...") as prt:
            nbr_points = len(values['cores'])
            prt.print(f"fit on {nbr_points} points")
            if nbr_points < MIN_POINTS:
                logging.getLogger(__name__).error(
                    "can not fit model for hostname=%s, not enouth points", hostname,
                )
                return 0.0, 0.0
            p_cores, p_static = np.polyfit(values["cores"], values["power"], deg=1)
            prt.print(f"power = {p_static:.3g} + cores * {p_cores:.3g}")
        return float(p_static), float(p_cores)

    def _predict(self, values: dict[str], parameters: object) -> dict[str]:
        p_static, p_cores = parameters


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
