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
DATA = "/srv/storage/videoimpact@storage3.rennes.grid5000.fr"
ENV_NAME = "https://api.grid5000.fr/sid/sites/rennes/public/rrichard/mendevi_env.yaml"
ROLES = ["magelan"]


def run_script(cmd: str | list[str], local: bool = False):
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
            job_name="mendevi",
            job_type=["deploy"],
            key="~/.ssh/id_ed25519.pub",
            walltime="48:00:00",
            # queue="production",  # "default", "testing", "besteffort"
        )
        .add_machine(roles=ROLES, cluster=CLUSTER, nodes=1)
    )
    with enoslib.G5k(conf) as (roles, _):  # get and release all grid5000 resources
        main_results = enoslib.run_command(cmd, roles=roles, background=True)
        log_files = [result.results_file for result in main_results]
        while log_files:
            for i, log_file in enumerate(log_files.copy()):
                for res in enoslib.run_command(f"cat {log_file}", roles=roles, on_error_continue=True):
                    res = json.loads(res.payload["stdout"])
                    if (msg := res.get("stderr", "")):
                        raise RuntimeError(msg)
                    elif "rc" in res:
                        print(res["stdout"])
                        del log_files[i]
                        break
            time.sleep(600)
