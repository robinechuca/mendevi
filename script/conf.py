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
            # key="~/.ssh/id_ed25519.pub",
            walltime="48:00:00",
            # queue="production",  # "default", "testing", "besteffort"
        )
        .add_machine(roles=ROLES, cluster=CLUSTER, nodes=1)
    )
    with enoslib.G5k(conf) as (roles, _):  # get and release all grid5000 resources
        main_results = enoslib.run_command(cmd, roles=roles)  # background=True
        for result in main_results:
            print(result.payload["stdout"])
        # log_files = [result.results_file for result in main_results]
        # while True:
        #     for log_file in log_files:
        #         for res in enoslib.run_command(f"cat {log_file}", roles=roles):
        #             res = json.loads(res.payload["stdout"])
        #             print(res.get("stdout", ""))
        #             print(res.get("stderr", ""))
        #         # AsyncCommandResult(
        #         #     host='paradoxe-27.rennes.grid5000.fr',
        #         #     task='mendevi encode ... _education_reel.webm',
        #         #     status='OK', payload={'started': 1, 'finished': 0, 'ansible_job_id': 'j345936901009.3728', 'results_file': '/root/.ansible_async/j345936901009.3728', 'changed': True, '_ansible_no_log': False})
        #         # import ipdb; ipdb.set_trace()
        #         # print(result.payload["stdout"])
        #     time.sleep(600)
        # # return result
