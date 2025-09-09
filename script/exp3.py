#!/usr/bin/env python3

"""Test the effect of vvc."""

import conf


CMD_ENCODE = [
    "mendevi", "encode",
    "--effort", "medium",
    "--encoder", "vvc",
    "--points", "2",
    *(f"-t{i}" for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]),
    f"{conf.DATA}/reference_netflix_aerial_uhd.mkv",
]
CMD_PROBE = [
    "mendevi", "probe",
    "--no-lpips-alex", "--no-lpips-vgg", "--no-psnr", "--no-ssim", "--no-uvq", "--no-vmaf",
    f"{conf.DATA}/sample*",
]


if __name__ == "__main__":
    conf.run_script(CMD_ENCODE, walltime="24:00:00")
    conf.run_script(CMD_PROBE, walltime="1:00:00")
