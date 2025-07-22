#!/usr/bin/env python3

"""Set the grid5000 configuration variables.

If you are using pyenv on grid5000, you must help ansible to find the right python interpreter.
In the file ``~/.ansible.cfg``, put the following content:
[defaults]
interpreter_python = /root/.pyenv/versions/3.13.3/envs/3.13/bin/python
"""

import json
import shlex
import subprocess
import time

import enoslib

CLUSTER = "paradoxe"
SERVERS = ["paradoxe-7.rennes.grid5000.fr"]  # optional
DATA = "/srv/storage/videoimpact@storage3.rennes.grid5000.fr"
ENV_NAME = "https://api.grid5000.fr/sid/sites/rennes/public/rrichard/mendevi_env.yaml"
ROLES = ["magelan"]
WALLTIME = "72:00:00"

SLEEP_INIT = 10.0  # initial sleeping time
SLEEP_FINAL = 600.0  # final sleeping time
SLEEP_TRANSITION = 3600.0  # the transition time between the init and final sleep


def run_script(cmd: str | list[str], local: bool=False):
    """Run a script on the grid."""
    # parse the argument
    assert isinstance(local, bool), local.__class__.__name__
    if isinstance(cmd, list):
        assert all(isinstance(e, str) for e in cmd), cmd
        cmd = " ".join(map(shlex.quote, cmd))
    else:
        assert isinstance(cmd, str), cmd.__class__.__name__

    # run localy
    if local:
        subprocess.run(cmd, shell=True)
        return

    # run on the grid
    enoslib.init_logging()
    conf = (  # doc: https://discovery.gitlabpages.inria.fr/enoslib/apidoc/infra.html#g5k-schema
        enoslib.G5kConf.from_settings(
            env_name=ENV_NAME,
            job_name="Mesures Encodage et Decodage Video",
            job_type=["deploy"],
            key="~/.ssh/id_ed25519.pub",
            walltime=WALLTIME,
            monitor="wattmetre_power_watt",
            # queue="production",  # "default", "testing", "besteffort"
        )
        .add_machine(roles=ROLES, cluster=CLUSTER, nodes=1, **({"servers": SERVERS} if SERVERS else {}))
    )
    sleep = SLEEP_INIT
    with enoslib.G5k(conf) as (roles, _):  # get and release all grid5000 resources
        main_results = enoslib.run_command(cmd, roles=roles, background=True)
        log_files = log_files = {result.results_file for result in main_results}
        while log_files:
            # waiting a moment
            # at the beginning, we wait SLEEP_INIT, and at the end, we wait SLEEP_FINAL
            # it takes n steps, with n = math.log(SLEEP_FINAL/SLEEP_INIT) / math.log(alpha)
            # with alpha = 1.0 + (SLEEP_FINAL - SLEEP_INIT) / SLEEP_TRANSITION
            # the full transition time take SLEEP_TRANSITION
            time.sleep(sleep)
            sleep *= 1.0 + (SLEEP_FINAL - SLEEP_INIT) / SLEEP_TRANSITION
            sleep = min(sleep, SLEEP_FINAL)
            for log_file in log_files.copy():
                for res in enoslib.run_command(f"cat {log_file}", roles=roles, on_error_continue=True):
                    res = json.loads(res.payload["stdout"])
                    if (msg := res.get("stderr", "")):
                        raise RuntimeError(msg)
                    elif "rc" in res:
                        print(res["stdout"])
                        log_files.remove(log_file)
