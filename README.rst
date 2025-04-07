MENDEVI
*******

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

* Presets ``fast``, ``medium`` and ``slow``.
* Codecs ``h264``, ``h265-hevc``, ``h266-vvc`` and ``av1``.
