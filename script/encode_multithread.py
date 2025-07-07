#!/usr/bin/env python3

"""Scripts with enoslib for grid5000."""

import conf

LOCAL = False  # set True to execute the tests on the local computer

# local data
RES_LOCAL = "~/Téléchargements"
VIDEO_LOCAL = "/data/dataset/video/despacito.mp4"

# grid5000 data
RES_G5K = conf.DATA
VIDEO_G5K = f"{conf.DATA}/lossless_video/bbb.webm"

CMD = [
    "mendevi", "encode",
    "--profile", "sd", "--profile", "uhd",
    "--preset", "medium",
    "--encoder", "libx264", "--encoder", "libx265", "--encoder", "libsvtav1",
    "--points", "2",
    *(f"-t{i}" for i in range(1, 17)),  # maximal supported value
    "--no-psnr", "--no-ssim", "--no-vmaf",
    "--out", f"{RES_LOCAL if LOCAL else RES_G5K}/encode_multithread_samples",
    "--res", f"{RES_LOCAL if LOCAL else RES_G5K}/encode_multithread_raw.json",
    VIDEO_LOCAL if LOCAL else VIDEO_G5K,
]

if __name__ == "__main__":
    conf.run_script(CMD, LOCAL)
