"""Extract simple constants in order to 'normalize' the values."""

import pathlib
import sqlite3

import cutcutcodec
import numpy as np
import tqdm
from context_verbose import Printer

from .create import is_sqlite
from .serialize import binary_to_list, binary_to_tensor

DURATION = 10.0  # slices duration in second


def _serializable_extractor(row: sqlite3.Row) -> dict:
    """Multiprocessing compatible version of `avg_slices`."""
    assert isinstance(row, sqlite3.Row), row.__class__.__name__
    data = {}

    # get cpu slices
    act_ps_dt = binary_to_list(row["act_ps_dt"])
    act_ps_core = 0.01 * binary_to_tensor(row["act_ps_core"])
    core: list[float] = avg_slices(act_ps_dt, act_ps_core, DURATION)

    # get rapl slices
    if row["act_rapl_dt"] and row["act_rapl_power"]:
        power: list[float] = avg_slices(
            binary_to_list(row["act_rapl_dt"]), binary_to_list(row["act_rapl_power"]), DURATION,
        )
        data["rapl"] = {"c": core[:len(power)], "p": power[:len(core)]}

    # get wattmeter slices
    if row["act_wattmeter_dt"] and row["act_wattmeter_power"]:
        power: list[float] = avg_slices(
            binary_to_list(row["act_wattmeter_dt"]),
            binary_to_list(row["act_wattmeter_power"]),
            DURATION,
        )
        data["wattmeter"] = {"c": core[:len(power)], "p": power[:len(core)]}

    # get gpu slices
    if row["act_gpu_dt"] and row["act_gpu_core"] and row["act_gpu_power"]:
        core: list[float] = avg_slices(
            binary_to_list(row["act_gpu_dt"]),
            binary_to_tensor(row["act_gpu_core"]),
            DURATION,
        )
        power: list[float] = avg_slices(
            binary_to_list(row["act_gpu_dt"]),
            binary_to_tensor(row["act_gpu_power"]),
            DURATION,
        )
        data["gpu"] = {"c": core[:len(power)], "p": power[:len(core)]}

    return data


def avg_slices(dt_array: np.ndarray, sample_array: np.ndarray, duration: float) -> list[float]:
    """Return the average sample for several overlapping windows of size duration."""
    assert isinstance(dt_array, np.ndarray), dt_array.__class__.__name__
    assert isinstance(sample_array, np.ndarray), sample_array.__class__.__name__
    assert len(dt_array) == len(sample_array), (dt_array.shape, sample_array.shape)
    assert isinstance(duration, float), duration.__class__.__name__
    assert duration > 0, duration

    # 2d -> 1d
    if sample_array.ndim == 2:
        sample_array = sample_array.sum(axis=1)

    # find slices boundaries
    half_duration = 0.5 * duration  # half overlapping
    indices, cumdt = [0], 0.0
    for i, dt_step in enumerate(dt_array.tolist()):
        cumdt += dt_step
        if cumdt >= half_duration:
            indices.append(i)
            cumdt -= half_duration  # no reset to 0 to keep synchronisation

    # cut slices
    slices = [
        (dt_array[i_start:i_end], sample_array[i_start:i_end])
        for i_start, i_end in zip(indices[:-2], indices[2:], strict=True)
    ]
    if len(indices) >= 2:
        slices.append((dt_array[indices[-2]:], sample_array[indices[-2]:]))
    else:
        slices.append((dt_array, sample_array))

    # integration
    return [float((vals * dts).sum() / dts.sum()) for dts, vals in slices]


def p_static_p_core(database: str | bytes | pathlib.Path) -> dict[str, tuple]:
    """Estimate for each hostname, the model P = P_static + c * P_core.

    Parameters
    ----------
    database : pathlike
        The path of the existing database to be updated.

    Returns
    -------
    cst : dict
        To each hostname, associate the estimation of (p_static, p_core).

    Examples
    --------
    >>> from mendevi.database.normalize import p_static_p_core
    >>> p_static_p_core("/data/dataset/merge.db")
    >>>

    """
    # open file
    database = pathlib.Path(database).expanduser()
    assert is_sqlite(database), database
    with (
        Printer("Estimate p_static and p_core for each hostname...") as prt,
        sqlite3.connect(f"file:{database}?mode=ro&immutable=1", uri=True, timeout=30) as conn,
    ):
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        hostnames = set(
            row_["env_hostname"]
            for row_ in cursor.execute("SELECT env_hostname FROM t_env_environment")
        )
        for i, hostname in enumerate(sorted(hostnames)):
            # preparation
            data = {
                "rapl_c": [], "rapl_p": [],
                "wattmeter_c": [], "wattmeter_p": [],
                "gpu_c": [], "gpu_p": [],
            }
            prt.print(f"hostname {i+1}/{len(hostnames)}: {hostname}")
            count = cursor.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT 1
                    FROM t_enc_encode
                    JOIN t_env_environment
                      ON t_env_environment.env_id = t_enc_encode.enc_env_id
                    WHERE t_env_environment.env_hostname = ?

                    UNION ALL

                    SELECT 1
                    FROM t_dec_decode
                    JOIN t_env_environment
                      ON t_env_environment.env_id = t_dec_decode.dec_env_id
                    WHERE t_env_environment.env_hostname = ?
                )
                """,
                (hostname, hostname),
            ).fetchone()["COUNT(*)"]

            # extract and smooth measures
            for slices in tqdm.tqdm(
                cutcutcodec.core.opti.parallel.imap(
                    _serializable_extractor,
                    cursor.execute(  # UNION ALL faster than UNION
                        """
                        SELECT
                            act_ps_dt,
                            act_ps_core,
                            act_rapl_dt,
                            act_rapl_power,
                            act_wattmeter_dt,
                            act_wattmeter_power,
                            act_gpu_dt,
                            act_gpu_core,
                            act_gpu_power
                        FROM t_enc_encode
                        JOIN t_act_activity ON t_act_activity.act_id = t_enc_encode.enc_act_id
                        JOIN t_env_environment ON t_env_environment.env_id = t_enc_encode.enc_env_id
                        WHERE t_env_environment.env_hostname = ?

                        UNION ALL

                        SELECT
                            act_ps_dt,
                            act_ps_core,
                            act_rapl_dt,
                            act_rapl_power,
                            act_wattmeter_dt,
                            act_wattmeter_power,
                            act_gpu_dt,
                            act_gpu_core,
                            act_gpu_power
                        FROM t_dec_decode
                        JOIN t_act_activity ON t_act_activity.act_id = t_dec_decode.dec_act_id
                        JOIN t_env_environment ON t_env_environment.env_id = t_dec_decode.dec_env_id
                        WHERE t_env_environment.env_hostname = ?
                        """,
                        (hostname, hostname),
                    ),
                ),
                dynamic_ncols=True,
                leave=False,
                smoothing=1e-8,
                total=count,
                unit="vid",
            ):  # no duplication issue thanks creation process
                if "rapl" in slices:
                    data["rapl_c"].extend(slices["rapl"]["c"])
                    data["rapl_p"].extend(slices["rapl"]["p"])
                if "wattmeter" in slices:
                    data["wattmeter_c"].extend(slices["wattmeter"]["c"])
                    data["wattmeter_p"].extend(slices["wattmeter"]["p"])
                if "gpu" in slices:
                    data["gpu_c"].extend(slices["gpu"]["c"])
                    data["gpu_p"].extend(slices["gpu"]["p"])

            # linear regression
            import matplotlib.pyplot as plt
            plt.scatter(data["rapl_c"], data["rapl_p"], alpha=0.1, label="rapl")
            plt.scatter(data["wattmeter_c"], data["wattmeter_p"], alpha=0.1, label="wattmeter")
            plt.scatter(data["gpu_c"], data["gpu_p"], alpha=0.1, label="gpu")
            plt.legend()
            plt.xlabel("taux d'utilisation")
            plt.ylabel("puissance (W)")
            plt.savefig(f"{hostname}.pdf", format="pdf")
            plt.show()
