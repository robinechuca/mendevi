"""Help to excecute a script on a node of grid'5000."""

import getpass
import hashlib
import json
import logging
import pathlib
import platform
import re
import subprocess
import time

import click
import orjson
import requests
from context_verbose import Printer

GOOD_REQ_STATUS = 200
SLEEP_FINAL = 600.0  # final sleeping time
SLEEP_INIT = 10.0  # initial sleeping time
SLEEP_TRANSITION = 3600.0  # the transition time between the init and final sleep


def _parse_args(prt: Printer, kwargs: dict) -> None:
    """Verification of the arguments."""
    # env_name
    kwargs["env_name"] = kwargs.get("env_name", "")
    if not kwargs["env_name"]:
        match len(env_name := guess_envname()):
            case 0:
                msg = (
                    "No environment .yaml images were found.\n"
                    "You must therefore specify it with the argument --env-name.\n"
                    'See: "https://www.grid5000.fr/w/Getting_Started'
                    '#Deploying_your_nodes_to_get_root_access_and_'
                    'create_your_own_experimental_environment".'
                )
                raise OSError(msg)
            case 1:
                kwargs["env_name"] = env_name[0]
            case _:
                logging.getLogger(__name__).warning(
                    "serveral env name were founded %s, please specify --env-name",
                    env_name,
                )
    else:
        assert isinstance(kwargs["env_name"], str), kwargs["env_name"].__class__.__name__
    prt.print(f"env_name: {kwargs['env_name']}")

    # walltime
    kwargs["walltime"] = kwargs.get("walltime") or "24:00:00"
    assert isinstance(kwargs["walltime"], str), kwargs["walltime"].__class__.__name__
    prt.print(f"walltime: {kwargs['walltime']}")

    # roles
    kwargs["roles"] = kwargs.get("roles", []) or guess_roles()
    assert isinstance(kwargs["roles"], tuple | list), kwargs["roles"].__class__.__name__
    kwargs["roles"] = list(kwargs["roles"])
    assert all(isinstance(r, str) for r in kwargs["roles"]), kwargs["roles"]
    prt.print(f"roles   : {kwargs['roles']}")

    # server
    kwargs["server"] = kwargs.get("server", ())
    assert isinstance(kwargs["server"], tuple), kwargs["server"].__class__.__name__
    assert all(isinstance(s, str) for s in kwargs["server"]), kwargs["server"]
    if kwargs["server"]:
        prt.print(f"servers : {', '.join(kwargs['server'])}")

    # cluster
    assert "cluster" in kwargs, kwargs
    assert isinstance(kwargs["cluster"], str), kwargs["cluster"].__class__.__name__
    prt.print(f"cluster : {kwargs['cluster']}")

    # nodes
    kwargs["nodes"] = kwargs.get("nodes", 1)
    assert isinstance(kwargs["nodes"], int), kwargs["nodes"].__class__.__name__
    prt.print(f"nodes   : {kwargs['nodes']}")


def guess_envname() -> list[str]:
    """Try to find the envname.

    Returns
    -------
    envnames : list[str]
        The candidate envnames, as a list of urls formated like:
        https://api.grid5000.fr/stable/sites/{{site}}/public/{{username}}/{{file}}

    """
    envnames: list[str] = []
    root = pathlib.Path.home() / "public"
    for path in root.rglob("*.yaml"):
        with path.open("r", encoding="utf-8") as file:
            content = file.read()
        if re.search(r"file:\s*https?://[\w.]+\.grid5000\.fr", content):
            envnames.append(
                "https://api.grid5000.fr/stable"
                f"/sites/{platform.node()[1:]}"  # "frennes", "fgrenoble", "ftoulouse" ...
                f"/public/{getpass.getuser()}"  # os.getlogin failed sometimes
                f"/{path.relative_to(root)}",
            )
    return envnames


def guess_roles() -> list[str]:
    """Return the roles list.

    Returns
    -------
    roles : list[str]
        The name of the group to which one belongs

    """
    roles = re.findall(
        r"\S+",
        subprocess.run(["id", "-Gn"], capture_output=True, check=True).stdout.decode("utf-8"),
    )
    return [r for r in roles if r != "g5k-users"]


def guess_servers() -> list[str]:
    """Return the available nodes address with a wattmeter."""
    # see oarnodes -l

    # get full node list
    try:
        servers = subprocess.run(["oarnodes", "--json"], capture_output=True, check=True)
    except FileNotFoundError:
        return []
    servers = orjson.loads(servers.stdout)

    # select with wattmeter
    servers = {
        ref: desc for ref, desc in servers.items()
        if (
            desc["wattmeter"] in {True, "yes", "YES", "ok", "OK"}
            and desc["deploy"]
        )
    }
    return list(servers)


def guess_storage() -> list[str]:
    """Return the accessible paths under "/srv/storage".

    If they have not been mounted for a while, NFS disks may be hidden with a simple ls command.
    This function attempts to predict the volume name in order to increase the chances of success.

    The rules are defined here: https://www.grid5000.fr/w/Group_Storage
    """
    # guessed with ls
    if not (root := pathlib.Path("/srv/storage")).exists():
        return []
    candidates = set(root.iterdir())

    # try to get server_name
    url = "https://www.grid5000.fr/w/Group_Storage"
    req = requests.get(url, timeout=60)
    if req.status_code != GOOD_REQ_STATUS:
        logging.getLogger(__name__).warning("the request %s failed", req)
        servers = []
    elif not (req := req.text):
        logging.getLogger(__name__).warning("the request %s gives an empty result", req)
        servers = []
    else:
        servers = re.findall(r"storage\d+\.\w+\.grid5000\.fr", req)

    # try to get storage_name
    prefixes = guess_roles()
    prefixes.extend(n for s in prefixes.copy() for n in s.split("-"))

    # merge candidates together with a cartesian product
    candidates |= {root / f"{p}@{s}" for s in set(servers) for p in set(prefixes)}

    # test if exists and permision (.exists() doesn't work with this nfs)
    storages: list[str] = []
    for path in candidates:
        try:
            with (path / "tmp_empty_mendevi").open("wb"):
                pass
        except (FileNotFoundError, PermissionError):
            continue
        (path / "tmp_empty_mendevi").unlink()
        storages.append(str(path))
    return storages


def is_g5k_frontend(*, fail: bool = True) -> bool:
    """Test if we are on the grid'5000 frontend."""
    assert isinstance(fail, bool), fail.__class__.__name__
    if pathlib.Path("/etc/grid5000").exists():
        return True
    if not fail:
        return False
    msg = (
        "You are not on the Grid'5000 frontend!\n"
        "The command 'mendevi g5k ...' must be executed exclusively from the frontend.\n"
        'See: "https://www.grid5000.fr/w/Getting_Started#Connect_to_a_Grid\'5000_access_machine"'
    )
    raise OSError(
        msg,
    )


def set_ansible_cfg() -> None:
    """Create and fill the file ~/.ansible.cfg."""
    path = pathlib.Path.home() / ".ansible.cfg"
    if not path.exists():
        with path.open("w", encoding="utf-8") as file:
            file.write("[defaults]\n")
            file.write("interpreter_python = /root/.pyenv/shims/python\n")


@click.command()
@click.argument("cmd", type=str)
@click.option(
    "-e", "--env-name",
    type=str,
    help="The kadeploy3 environment to use.",
)
@click.option(
    "-w", "--walltime",
    type=str,
    help="Job duration.",
)
@click.option(
    "-s", "server",
    type=str,
    multiple=True,
    help="The specific node name.",
)
@click.option(
    "-c", "--cluster",
    type=str,
    help="The generique cluster name to use.",
)
@click.option(
    "-r", "roles",
    type=str,
    multiple=True,
    help="The specific role to use.",
)
@click.option(
    "-n", "--nodes",
    type=int,
    default=1,
    help="The number of nodes to be deployed.",
)
def main(cmd: str, **kwargs: dict) -> None:
    """Deploy a grid'5000 node and run a mendevi script inside it.

    \b
    Parameters
    ----------
    **kwargs: dict
        Please refer to the detailed arguments below.
    cmd : str
        The mendevi command to be executed on the deployed node.
        When a path begins with ./, this part is automatically replaced by the shared folder file.
    env_name : str, optional
        The kadeploy3 yaml path file environment to use.
        By default, the first environment found is used.
    walltime : str, default=24:00:00
        The maximum reservation time for the node.
        If the script finishes before this time, the resources are released before the expiry date.
    roles : tuple[str], default=autodetect
        The role to used, by default, the list is autodetected with :py:func:`guess_roles`.
    server : tuple[str], optional
        The specific node names (ex: ("paradoxe-1.rennes.grid5000.fr",)).
    cluster : str
        The name of the cluster to used (ex: "paradoxe").
    nodes : int, default=1
        The number of nodes to deploy (incompatible with ``server``).

    """
    is_g5k_frontend()
    set_ansible_cfg()
    with Printer("Parse configuration...") as prt:
        assert isinstance(cmd, str), cmd.__class__.__name__
        if " ./" in cmd and len(data := guess_storage()) == 1:
            cmd = re.split(r"\s+\./", cmd)
            cmd = f"{cmd[0]}{''.join(f' {data[0]}/{c}' for c in cmd[1:])}"
        prt.print(f"cmd     : {cmd}")
        _parse_args(prt, kwargs)

    # run on the grid
    import enoslib  # noqa: PLC0415
    enoslib.init_logging()
    conf = (
        # doc: https://discovery.gitlabpages.inria.fr/enoslib/apidoc/infra.html#g5k-schema
        enoslib.G5kConf.from_settings(
            env_name=kwargs["env_name"],
            job_name=f"mendevi {hashlib.md5(cmd.encode('utf-8')).hexdigest()}",
            job_type=["deploy", "exotic"],
            walltime=kwargs["walltime"],
            monitor="wattmetre_power_watt",
            # queue="production",  # "default", "testing", "besteffort"
        )
        .add_machine(
            roles=kwargs["roles"],
            cluster=kwargs["cluster"],
            nodes=kwargs["nodes"],
            **({"servers": list(kwargs["server"])} if kwargs["server"] else {}),
        )
    )
    sleep = SLEEP_INIT
    warnings: set[str] = set()  # the displayed warnings
    with enoslib.G5k(conf) as (roles, _):  # get and release all grid5000 resources
        main_results = enoslib.run_command(cmd, roles=roles, background=True)
        log_files = {result.results_file for result in main_results}
        while log_files:
            # waiting a moment
            # at the beginning, we wait SLEEP_INIT, and at the end, we wait SLEEP_FINAL
            # it takes n steps, with n = math.log(SLEEP_FINAL/SLEEP_INIT) / math.log(alpha)
            # with alpha = 1.0 + (SLEEP_FINAL - SLEEP_INIT) / SLEEP_TRANSITION
            # the full transition time take SLEEP_TRANSITION
            time.sleep(sleep)
            sleep *= 1.0 + (SLEEP_FINAL - SLEEP_INIT) / SLEEP_TRANSITION
            sleep = min(sleep, SLEEP_FINAL)
            for log_file, res in [
                (log_file_, res_)
                for log_file_ in log_files.copy()
                for res_ in enoslib.run_command(
                    (
                        f'if [ -f "{log_file_}" ]; '
                        f'then cat "{log_file_}"; '
                        'else echo "<no-log-yet>"; fi'
                    ),
                    roles=roles,
                    on_error_continue=True,
                )
            ]:
                # display warnings
                for msg in res.payload.get("warnings", []):
                    if msg not in warnings:
                        logging.getLogger(__name__).warning(msg)
                        warnings.add(msg)

                # skip when file log is not yet created
                try:
                    if res.payload["stdout"] == "<no-log-yet>":
                        continue
                except KeyError:
                    logging.getLogger(__name__).exception("stop communication with %s", log_files)
                    log_files.remove(log_file)
                    continue

                # get job result
                try:
                    res_ = json.loads(res.payload["stdout"])  # orjson failed
                except json.JSONDecodeError:
                    logging.getLogger(__name__).exception(res.payload)
                    raise
                if res_.get("changed", False) or "rc" in res_:
                    print(res_.get("stdout", ""))
                    logging.getLogger(__name__).error(res_.get("stderr", ""))
                    log_files.remove(log_file)
