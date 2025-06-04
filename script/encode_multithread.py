#!/usr/bin/env python3

"""Scripts with enoslib for grid5000.

If you are using pyenv on grid5000, you must help ansible to find the right python interpreter.
In the file ``~/.ansible.cfg``, put the following content:
[defaults]
interpreter_python = /root/.pyenv/versions/3.13.3/envs/3.13/bin/python
"""

import conf

LOCAL = True  # set True to execute the tests on the local computer

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
    "-t1", "-t2", "-t3", "-t4", "-t6", "-t8", "-t12", "-t16",  # 24, 32, 52 if we can
    "--no-psnr", "--no-ssim", "--no-vmaf",
    "--out", f"{RES_LOCAL if LOCAL else RES_G5K}/encode_multithread_samples",
    "--res", f"{RES_LOCAL if LOCAL else RES_G5K}/encode_multithread.json",
    VIDEO_LOCAL if LOCAL else VIDEO_G5K,
]


if __name__ == "__main__":
    conf.run_script(CMD, LOCAL)
