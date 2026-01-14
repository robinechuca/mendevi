"""Search for available torrent files."""

import pathlib
import shutil

import requests
from context_verbose import Printer

from mendevi.utils import get_project_root


def get_torrent(name: str) -> pathlib.Path:
    """Retrieve a torrent from its full name.

    Parameters
    ----------
    name : str
        The full torrent name, for example "multithread.db.xz.torrent".

    Returns
    -------
    path : pathlib.Path
        The full path of the torrent.

    Raises
    ------
    KeyError
        If the requested torrent is not included in the list of possible torrents.

    """
    assert isinstance(name, str), name.__class__.__name__

    # look in cachedir
    cachedir = pathlib.Path.home() / ".cache" / "mendevi"
    cachedir.mkdir(mode=0o777, parents=True, exist_ok=True)
    if (file := cachedir / name).exists():
        return file

    # look on the local cloned mendevi git
    local = {p.name: p for p in probe_local_torrent()}
    if name in local:
        # copy in mendevi cachedir for transmission permission
        shutil.copy(local[name], cachedir / name)
        return cachedir / name

    # download online
    with Printer(f"Download {name!r}...", color="green") as prt:
        # look avalable list
        prt.print("get url")
        online = probe_online_torrent()
        if name not in online:
            msg = f"{name!r} not in {', '.join(sorted(set(local) | set(online)))}"
            raise KeyError(msg)

        # download torrent file
        prt.print(f"download {online[name]}")
        req = requests.get(online[name], stream=True, timeout=60)
        req.raise_for_status()
        torrent_data = req.raw.data
        prt.print(f"{len(torrent_data)} bytes retrieved")
        assert torrent_data

    # write the file
    with file.open("wb") as raw:
        raw.write(torrent_data)
    return file


def probe_online_torrent() -> dict[str, str]:
    """Search on GitLab online for the names of available torrents.

    Returns
    -------
    torrents : dict
        For each torrent name, provide the URL for downloading it.

    Examples
    --------
    >>> from mendevi.download.torrent_finder import probe_online_torrent
    >>> sorted(probe_online_torrent())
    ['duration.db.xz.torrent', 'multithread.db.xz.torrent', 'x264_vs_openh264.db.xz.torrent']
    >>>

    """
    url = "https://gitlab.inria.fr/api/v4/projects/rrichard%2Fmendevi/repository/tree?path=dataset"
    req = requests.get(url, timeout=60)
    req.raise_for_status()
    all_files = req.json()
    return {
        f["name"]: f"https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/{f['path']}"
        for f in all_files if f["name"].endswith(".torrent")
    }


def probe_local_torrent() -> set[pathlib.Path]:
    """Search for the names of locally accessible torrents (if the mendevi repository is cloned).

    Returns
    -------
    torrents : set[pathlib.Path]
        Provide all the local torrent files.

    Examples
    --------
    >>> from mendevi.download.torrent_finder import probe_local_torrent
    >>> sorted(t.name for t in probe_local_torrent())
    ['duration.db.xz.torrent', 'multithread.db.xz.torrent', 'x264_vs_openh264.db.xz.torrent']
    >>>

    """
    return set((get_project_root().parent / "dataset").glob("*.torrent"))
