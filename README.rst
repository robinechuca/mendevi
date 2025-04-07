MENDEVI
*******

**Me**sures d'**En**codage et **Dé**codage **Vi**déo.

.. image:: https://img.shields.io/badge/License-MIT-green.svg
    :alt: [license MIT]
    :target: https://opensource.org/licenses/MIT

.. image:: https://img.shields.io/badge/linting-pylint-green
    :alt: [linting: pylint]
    :target: https://github.com/pylint-dev/pylint


Description
===========

This module performs video encoding and decoding measurements.
It compares the codecs ``h264``, ``h265-hevc``, ``h266-vvc`` and `av1`
for the for ``sd``, ``hd``, ``hdr`` and ``uhd`` scenarios.

Codecs are tested at different bitrates and presets.
Energy measurements are catched with RAPL and an external wattmeter on GRID5000.
Distortions are measured using the ``psnr``, ``ssim`` and ``vmaf`` metrics.


Features
========

* Codecs ``h264:libx264``, ``h265-hevc:libx265``, ``h266-vvc:vvenc`` and ``av1:libsvtav1``.
* Encoding presets ``fast``, ``medium`` and ``slow``.
* The ``sd``, ``hd``, ``hdr`` and ``uhd`` profiles are detailed in `profiles.py <https://gitlab.inria.fr/rrichard/mendevi/profiles.py>`_.


Installation
============

.. code:: shell

    git clone https://gitlab.inria.fr/rrichard/mendevi.git ~/mendevi_git
    cd ~/mendevi_git
    pyenv activate mendevi  # to be sure to be in a virtual env
    pip -v install --editable .
