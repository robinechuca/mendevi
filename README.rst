.. rst syntax: https://deusyss.developpez.com/tutoriels/Python/SphinxDoc/
.. version conv: https://peps.python.org/pep-0440/

**Me**\asures of **En**\coding and **De**\coding of **Vi**\deos.
****************************************************************

.. image:: https://img.shields.io/badge/License-GPL-green.svg
    :alt: [license GPL]
    :target: https://opensource.org/license/gpl-3-0

.. image:: https://img.shields.io/badge/linting-pylint-green
    :alt: [linting: pylint]
    :target: https://github.com/pylint-dev/pylint

.. image:: https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue
    :alt: [versions]

.. image:: https://static.pepy.tech/badge/mendevi
    :alt: [downloads]
    :target: https://www.pepy.tech/projects/mendevi

.. image:: https://readthedocs.org/projects/mendevi/badge/?version=latest
    :alt: [documentation]
    :target: https://mendevi.readthedocs.io

Useful links:
`Binary Installers <https://pypi.org/project/mendevi>`_ |
`Source Repository <https://gitlab.inria.fr/rrichard/mendevi>`_ |
`Online Documentation <https://mendevi.readthedocs.io>`_ |


Description
===========

This module performs **energy** and **metrics** measurements on video, for encoding and decoding.
It also provides a detailed **dataset**.

It manages the following parameters:

#. It supports the ``libx264``, ``libx265``, ``libvpx-vp9``, ``libsvtav1`` and ``vvc`` encoders.
#. Distortions are measured using the ``lpips``, ``psnr``, ``ssim`` and ``vmaf`` metrics.
#. Complexity are measured using the ``rms_sobel`` and ``rms_time_diff`` metrics.
#. Encoding efforts are ``fast``, ``medium`` and ``slow``.
#. It takes care about the colorspaces.
#. Iterate over different ``effort``, ``encoder``, ``mode``, ``quality``, ``threads``, ``fps``, ``resolution`` and ``pix_fmt``.
#. Energy measurements are catched with ``RAPL`` and an external wattmeter on ``grid'5000``.
#. Get the ``cpu`` and ``ram`` activity.
#. Get a full environment context, including harware and software version.
#. It support the mode (constant bitrate) ``cbr`` and (constant quality) ``vbr``.


Pipeline
========

This is the pipeline used for measurements:

.. image:: https://mendevi.readthedocs.io/latest/_images/pipeline.svg
    :alt: Pipeline diagram


Example of result
=================

Example of rate distortion curve:

.. code:: shell

    mendevi plot mendevi.db -x bitrate -y psnr -y ssim -wx profile -c encoder


.. image:: https://mendevi.readthedocs.io/latest/_images/rate_distortion.svg
    :alt: Result plot of rate distortion


Example of energy per encoder:

.. code:: shell

    mendevi plot mendevi.db -x quality -y energy -wx profile -wy mode -c encoder -m effort


.. image:: https://mendevi.readthedocs.io/latest/_images/energy.svg
    :alt: Result plot of encoding energy


Alternatives
============

#. The `MVCD database <https://github.com/cd-athena/MVCD>`_ also includes video encoding and decoding energy measurements.
#. The `COCONUT database <https://github.com/cd-athena/COCONUT>`_ also includes video decoding measurements.
#. The `VEED-dataset <https://github.com/cd-athena/VEED-dataset/tree/main>`_ offers a comprehensive LCA and GPU measurements.
#. The `CTC videos <https://dash-large-files.akamaized.net/WAVE/3GPP/5GVideo/ReferenceSequences/>`_ are used for the tests.
