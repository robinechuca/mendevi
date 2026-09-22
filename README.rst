.. rst syntax: https://deusyss.developpez.com/tutoriels/Python/SphinxDoc/
.. version conv: https://peps.python.org/pep-0440/

**Me**\asures of **En**\coding and **De**\coding of **Vi**\deos.
****************************************************************

.. image:: https://img.shields.io/badge/License-GPL-green.svg
    :alt: [license GPL]
    :target: https://opensource.org/license/gpl-3-0

.. image:: https://img.shields.io/badge/linting-ruff-green
    :alt: [linting: ruff]
    :target: https://docs.astral.sh/ruff

.. image:: https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue
    :alt: [versions]

.. image:: https://static.pepy.tech/badge/mendevi
    :alt: [downloads]
    :target: https://www.pepy.tech/projects/mendevi

.. image:: https://readthedocs.org/projects/mendevi/badge/?version=latest
    :alt: [documentation]
    :target: https://mendevi.readthedocs.io

Useful links:
`Binary Installers <https://pypi.org/project/mendevi/>`_ |
`Source Repository <https://gitlab.inria.fr/rrichard/mendevi/>`_ |
`Online Documentation <https://mendevi.readthedocs.io/>`_ |


Description
===========

Context
^^^^^^^

This module is developed by the `INRIA COMPACT team <https://www.inria.fr/fr/compact>`_, as part of the `VideoImpact <https://project.inria.fr/videoimpact/>`_ project.

Project
^^^^^^^

This Python module performs **energy consumption** and **video metrics** measurements for both **video encoding and decoding workflows**.
It includes **comprehensive ready-to-use datasets**, available as exhaustive SQL databases and lightweight JSON representations, as well as pretrained **predictive models** for energy and quality estimation.
The framework provides advanced visualization tools for **generating complex matplotlib figures**, executable from a single command-line interface.

It manages the following parameters:

#. It supports the ``libx264``, ``libopenh264``, ``libx265``, ``libvpx-vp9``, ``libaom-av1``, ``libsvtav1``, ``librav1e`` and ``vvc`` cpu encoders.
#. It supports the ``h264_nvenc``, ``hevc_nvenc``, ``av1_nvenc`` and ``*_vaapi`` gpu encoders.
#. Distortions are measured using the ``lpips``, ``psnr``, ``ssim``, ``vif`` and ``vmaf`` metrics.
#. Complexity metrics are measured using the ``rms_sobel``, ``rms_time_diff``, ``spatial_dct`` and ``temporal_dct`` metrics.
#. Encoding efforts are ``fast``, ``medium`` and ``slow``.
#. It handles color-related parameters, including color range, transfer characteristics, and color primaries (``range``, ``transfer`` and ``primaries``).
#. Iterate over different ``effort``, ``encoder``, ``mode``, ``quality``, ``threads``, ``fps``, ``resolution`` and ``pix_fmt``.
#. Energy measurements are captured with ``RAPL`` and an external wattmeter on ``grid'5000``.
#. Get the ``cpu``, ``gpu``, ``ram`` and ``temperature`` activity.
#. Get a full environment context, including hardware and software version.
#. It supports the mode (constant bitrate) ``cbr`` and (constant quality) ``vbr``.
#. Ability to ``modify ffmpeg commands`` on the fly to perform specific tests, giving your own defined callback function.
#. It takes care to ``transfer files to RAM`` if possible to avoid biases related to storage space access.
#. Provides a guide to compile ffmpeg with all optimizations in order to ``compare encoders/decoders at their limits``.

.. caution::
    The entire code was written by hand, without the use of AI, including the kernel module cutcutcodec!


Pipeline
========

This is the pipeline used for measurements:

.. image:: https://mendevi.readthedocs.io/latest/_images/pipeline.svg
    :alt: Pipeline diagram


Example of result
=================

Download and merge two datasets with this bash command:

.. code:: shell

    mendevi merge svtav1_vs_rav1e_vs_aom.db x264_vs_openh264.db -o /tmp/av1_h264.db

Example of energy and rate distortion video encoding, on a single video for several profiles:

.. code:: shell

    mendevi plot /tmp/av1_h264.db -x rate -x energy -y vmaf -c encoder -m effort -wy profile -f "ref_stem=='park_joy'"

.. image:: https://mendevi.readthedocs.io/latest/_images/example.svg
    :alt: Example plot


Alternatives
============

#. The `GREEM <https://github.com/cd-athena/GREEM>`_ video encoding measurement tool.
#. The `MVCD database <https://github.com/cd-athena/MVCD>`_ also includes video encoding and decoding energy measurements.
#. The `COCONUT database <https://github.com/cd-athena/COCONUT>`_ also includes video decoding measurements.
#. The `SEED and VEED dataset <https://github.com/cd-athena/VEED-dataset>`_ offers a comprehensive LCA and GPU measurements.


Citation
========

If this work is helpful for your research, please consider citing it.

.. code::

    @software{mendevi,
        author = {Robin Richard and Thomas Maugey and Anne-Cecile Orgerie},
        title = {{Mendevi}: Measures of Encoding and Decoding of Videos},
        date = {2026-09-12},
        url = {https://gitlab.inria.fr/rrichard/mendevi},
        version = {latest},
        license = {GPLv3},
        note = {Python software and dataset for measuring video encoding and decoding},
        keywords = {video encoding, decoding, energy, complexity, quality, dataset},
        organization = {Inria},
        location = {Rennes, France},
    }
