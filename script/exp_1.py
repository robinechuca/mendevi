#!/usr/bin/env python3

"""Test the effect of the video."""

import conf

CMD = [
    "mendevi", "encode",
    "--effort", "medium",
    "--encoder", "libx264", "--encoder", "libx265", "--encoder", "libsvtav1", "--encoder", "libvpx-vp9",
    "--points", "2",
    *(f"-t{i}" for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]),
    f"{conf.DATA}/reference_netflix_aerial_uhd.mkv",
]

if __name__ == "__main__":
    conf.run_script(CMD, walltime="00:30:00")
