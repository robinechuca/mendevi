MENDEVI
*******

**Me** sures d'**En** codage et **Dé** codage **Vi** déo.

.. image:: https://img.shields.io/badge/License-MIT-green.svg
    :alt: [license MIT]
    :target: https://opensource.org/licenses/MIT

.. image:: https://img.shields.io/badge/linting-pylint-green
    :alt: [linting: pylint]
    :target: https://github.com/pylint-dev/pylint


Description
===========

This module performs video encoding and decoding measurements.
It compares differents codecs in differents scenarios.

Codecs are tested at different bitrates and presets.
Energy measurements are catched with RAPL and an external wattmeter on GRID5000.
Distortions are measured using the ``psnr``, ``ssim`` and ``vmaf`` metrics.


Installation
============

.. code:: shell

    git clone https://gitlab.inria.fr/rrichard/mendevi.git ~/mendevi_git
    cd ~/mendevi_git
    pyenv activate mendevi  # to be sure to be in a virtual env
    pip -v install --editable .

Features
========

General
-------

#. Codecs ``h264:libx264``, ``h265-hevc:libx265``, ``h266-vvc:vvenc``, ``vp9:libvpx`` and ``av1:libsvtav1``.
#. Encoding presets ``fast``, ``medium`` and ``slow``.
#. The ``sd``, ``hd``, ``uhd`` and ``hd4k`` profiles are detailed in `profiles.py <https://gitlab.inria.fr/rrichard/mendevi/-/blob/main/mendevi/profiles.py>`_.

Encode
------

To generate the encoding database for the ``my_video.mp4`` video, you can use the following command:

.. code:: shell

    mendevi encode -p sd my_video.mp4


For each encoded file name, the information in the json file ``encode.json`` is as follows:

.. code:: yaml

    {
        "cmd": ["ffmpeg", ...],  # the exact arguments used for encoding
        "compression_ratio": 123.456,  # raw file size divided by encoded file size
        "crf": 28.1,  # the compression effort between 1.0 and 63.0
        "encode_context": {  # machine information and library versions
            "hostname": "paradoxe-1.rennes.grid5000.fr",
            ...,
        },
        "encode_duration": 123.456,  # encoding time in seconds
        "encode_idle_rapl": {  # RAPL cpu measurements of the IDLE based on 'perf' (power/energy-pkg/)
            "dt": [0.05, 0.05, ...],  # the duration of each interval in seconds
            "power": 123.456,  # the total energy divided by the duration, in watt
            "powers": [123.123, ...],  # the average power in watt in each interval
        }
        "encode_idle_usage": {  # CPU and RAM measure of the IDLE
            "cpu":  5.0,  # the average cumulated usage of all logical cpus
            "cpus": [[5.0, 0.0], ...],  # the detailed usage of each cpu in %
            "dt": [0.05, 0.05, ...],  # the duration of each interval in seconds
            "ram": [3952903680, 3952903680, ...],  # the ram usage in bytes
        }
        "encode_idle_wattmeter": {  # external wattmeter on grid5000 servers, measure the IDLE
            "dt": [0.05, 0.05, ...],  # the duration of each interval in seconds
            "power": 123.456,  # the total energy divided by the duration, in watt
            "powers": [123.123, ...],  # the average power in watt in each interval
        }
        "encode_rapl": {  # RAPL cpu measurements based on 'perf' (power/energy-pkg/)
            "dt": [0.05, 0.05, ...],  # the duration of each interval in seconds
            "energy": 123.456,  # total energy in joules used by the cpu during encoding
            "power": 123.456,  # the average power in watt
            "powers": [123.123, ...],  # the average power in watt in each interval
        }
        "encode_start": 1744114180.8672826,  # absolute start timestamp in seconds
        "encode_stop": 1744114198.7116294,  # absolute stop timestyamp in seconds
        "encode_threads": 8,  # the number of threads used durring encoding
        "encode_usage": {  # CPU and RAM usage with psutil
            "cpu":  20.0,  # the average cumulated usage of all logical cpus
            "cpus": [[20.0, 0.0], ...],  # the detailed usage of each cpu in %
            "dt": [0.05, 0.05, ...],  # the duration of each interval in seconds
            "ram": [4952903680, 4952903680, ...],  # the ram usage in bytes
        }
        "encode_wattmeter": {  # external wattmeter on grid5000 servers
            "dt": [0.05, 0.05, ...],  # the duration of each interval in seconds
            "energy": 123.456,  # total energy in joules used by the server during encoding
            "power": 123.456,  # the average power in watt
            "powers": [123.123, ...],  # the average power in watt in each interval
        },
        "encoder": "libx264",  # the name of the encoder
        "file": "bbb",  # the stem name of the source video file
        "frames": [  # the metadata of all frames
            {
                "best_effort_timestamp_time": 0.0,
                ...,
                "color_primaries": "smpte170m",
                ...,
                "pict_type": "I",
            },
            ...,
        ],
        "preset": "medium",  # the equivalent preset used for encoding
        "profile": "sd",  # the general profile used
        "psnr": [40.0, ...],  # the psnr (6, 1, 1) metric for each frame
        "rate": 123.456,  # average video bit rate in bit/second
        "size": 123456,  # final file size in bytes
        "ssim": [0.89, ...],  # the ssim (6, 1, 1) metric for each frame, gaussian window 11x11
        "uvq": [3.5, ...],  # the google uvq metric for each second of video
        "video_duration": 123.456,  # the exact duration of the video in second
        "vmaf": [70.0, ...],  # the netflix metric for each frame.
    }


Decode
------

Not yet implemented


Alternatives
============

#. The `MVCD database <https://github.com/cd-athena/MVCD>`_ also includes video encoding and decoding energy measurements.
#. The `COCONUT database <https://github.com/cd-athena/COCONUT>`_ also includes video decoding measurements.
