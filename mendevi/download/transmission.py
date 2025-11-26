"""Interacted with transmission-daemon."""

import logging
import pathlib
import subprocess
import time

import orjson
import tqdm
from context_verbose import Printer


def add_torrent(
    torrent: pathlib.Path, download_dir: pathlib.Path | None = None,
) -> pathlib.Path:
    """Add the torrent to transmission.

    Parameters
    ----------
    torrent : pathlib.Path
        The torrent file to be added.
    download_dir : pathlib.Path, default=~/.cache/mendevi/
        The download_dir in which to download the torrent content.

    Returns
    -------
    file : pathlib.Path
        Return the downloaded file path, related to the torrent.

    """
    # verifications
    assert isinstance(torrent, pathlib.Path), torrent.__class__.__name__
    assert torrent.is_file(), torrent
    if download_dir is None:
        download_dir = pathlib.Path.home() / ".cache" / "mendevi"
        download_dir.mkdir(mode=0o777, parents=True, exist_ok=True)
    else:
        assert isinstance(download_dir, pathlib.Path), download_dir.__class__.__name__
        assert download_dir.is_dir(download_dir)

    # shortcut
    final_file = download_dir / torrent.stem
    if (final_file).exists():
        return final_file

    # add torrent
    test_transmission_is_installed()  # after shortcut
    with Printer(f"Add {torrent.name!r} to transmission...", color="green") as prt:
        try:
            out = subprocess.run(
                [
                    "transmission-remote",
                    "--add", str(torrent),
                    "--download-dir", str(download_dir),
                ],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as err:
            msg = "the transmission-daemon package appears to be corrupted"
            raise ImportError(msg) from err
        prt.print(out.stdout.decode().strip())

    # download content
    wait_until_finished(torrent.stem)

    return final_file


def test_transmission_is_installed() -> None:
    """Ensures that transmission-daemon has been installed correctly.

    Raises
    ------
    ImportError
        If transmission-daemon is not well installed

    """
    try:
        out = subprocess.run(["transmission-remote", "--version"], check=True, capture_output=True)
    except FileNotFoundError as err:
        msg = (
            "please install transmission-daemon "
            "(https://mendevi.readthedocs.io/latest/developer_guide/installation.html#transmission)"
        )
        raise ImportError(
            msg,
        ) from err
    if not (out.stdout or out.stderr):
        msg = "the transmission-daemon package appears to be corrupted"
        raise logging.getLogger(__name__).warning(msg)


def wait_until_finished(name: str) -> None:
    """Display the progress bar of the torrent download."""
    with Printer(f"Download {name!r} (transmission-remote -l)...", color="green") as prt:
        load = tqdm.tqdm(
            dynamic_ncols=True,
            leave=True,
            smoothing=1e-6,
            total=None,
            unit="Mo",
        )
        while True:
            out = subprocess.run(
                ["transmission-remote", "--json", "--list"],
                check=True,
                capture_output=True,
            )
            try:
                states = orjson.loads(out.stdout)
            except orjson.JSONDecodeError as err:
                msg = f"the transmission-daemon package appears to be corrupted, {out.stdout}"
                raise ImportError(
                    msg,
                ) from err
            if len(state := [t for t in states["arguments"]["torrents"] if t["name"] == name]) == 0:
                msg = f"the torrent {name} is not in the transmission-remote --list"
                raise KeyError(msg)
            state = state.pop()
            if state["errorString"]:
                load.set_description(state["errorString"])
            else:
                load.set_description(f"downloads from {state['peersSendingToUs']} pairs")
            load.total = state["sizeWhenDone"]//1_000_000
            load.update(load.total - state["leftUntilDone"]//1_000_000 - load.n)
            if state["leftUntilDone"] == 0:
                load.close()
                break
            time.sleep(1.0)
        prt.print_time()
