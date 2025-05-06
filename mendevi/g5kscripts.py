#!/usr/bin/env python3

"""Scripts with enoslib for grid5000."""

import enoslib as en

DATA = "/srv/storage/videoimpact@storage3.rennes.grid5000.fr"
CLUSTER = "paradoxe"


if __name__ == "__main__":
    _ = en.init_logging()
    conf = (
        en.G5kConf.from_settings(
            job_name="mendevi",
            walltime="0:10:00",
            job_type=["deploy"],
            env_name="my-custom-environment.yaml",
        )
        .add_machine(roles=["magelan"], cluster=CLUSTER, nodes=1)
    )
    with en.G5k(conf) as provider:  # Release all Grid'5000 resources
        provider = en.G5k(conf)
        roles, networks = provider.init()
        results = en.run_command("lsb_release -a", roles=roles)
        for result in results:
            print(result.payload["stdout"])
    