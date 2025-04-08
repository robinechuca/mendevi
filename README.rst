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
#. 

Encode
------

.. code:: json

    {
        "args": ["ffmpeg", ...],  # the exact arguments used for encoding
        "compression_ratio": 123.456,  # raw file size divided by encoded file size
        "context": ...,  # machine information and library versions
        "crf": 28.1,  # the compression effort between 1.0 and 63.0
    }

Decode
------

Not yet implemented


Alternatives
============

#. The `MVCD database <https://github.com/cd-athena/MVCD>`_ also includes video encoding and decoding energy measurements.
#. The `COCONUT database <https://github.com/cd-athena/COCONUT>`_ also includes video decoding measurements.
