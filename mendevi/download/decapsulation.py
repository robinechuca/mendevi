"""Automatate the decapsulation process."""

import pathlib
import re

from .decompress import decompress
from .torrent_finder import get_torrent
from .transmission import add_torrent


def retrive_file(file: pathlib.Path | str) -> pathlib.Path:
    """Attempt to retrieve the file.

    Parameters
    ----------
    file : pathlike
        The name or the identifier of the file you want to retrive.

    Returns
    -------
    decapsulated_file : pathlib.Path
        The final unencapsulated file.

    """
    file = pathlib.Path(file).expanduser()

    # handle <...>
    if re.match(r"^<.+>$", file.name):
        name = re.sub(r"^<(.+?)(?:\.xz(?:\.torrent)?)?>$", r"\1", file.name) + ".xz.torrent"
        return retrive_file(file.parent / name)

    # remove .xz.torrent
    file = file.parent / re.sub(r"\.xz(?:\.torrent)?$", "", file.name)

    # shortcut
    if file.exists():
        return file

    # handle .xz
    if (prev_file := file.parent / f"{file.name}.xz").exists():
        return decompress(prev_file)

    # handle .torrent
    if (prev_prev_file := prev_file.parent / f"{prev_file.name}.torrent").exists():
        return retrive_file(add_torrent(prev_prev_file))

    # general case
    return retrive_file(get_torrent(prev_prev_file.name))
