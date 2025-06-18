#!/usr/bin/env python3

"""Test the wattmeter on grid5000."""

import conf

CMD = [
    "python",
    "-c",
    (
        "import platform, time; from mendevi.g5kpower import g5kpower; "
        "print(g5kpower(platform.node(), time.time()-10.0, 5.0))"
    )
]

if __name__ == "__main__":
    conf.run_script(CMD, local=False)
