#!/usr/bin/env python3

"""Query the GPUs activity."""

import logging
import time

import pynvml  # uv pip install nvidia-ml-py


# initialisation
try:
    pynvml.nvmlInit()
except pynvml.NVMLError as err:
    logging.warning(err)
    GPUS = 0
else:
    GPUS: int = pynvml.nvmlDeviceGetCount()


def measure():
    for i in range(GPUS):
        hand = pynvml.nvmlDeviceGetHandleByIndex(i)
        power = pynvml.nvmlDeviceGetPowerUsage(hand) / 1000.0  # in Watts
        util = pynvml.nvmlDeviceGetUtilizationRates(hand).gpu  # in %
        mem = pynvml.nvmlDeviceGetMemoryInfo(h).used  # in bytes
