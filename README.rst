.. rst syntax: https://deusyss.developpez.com/tutoriels/Python/SphinxDoc/
.. version conv: https://peps.python.org/pep-0440/

**Me**\sures d'**En**\codage et **Dé**\codage **Vi**\déo.
*********************************************************

.. image:: https://img.shields.io/badge/License-GPL-green.svg
    :alt: [license GPL]
    :target: https://opensource.org/license/gpl-3-0

.. image:: https://img.shields.io/badge/linting-pylint-green
    :alt: [linting: pylint]
    :target: https://github.com/pylint-dev/pylint

.. image:: https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue
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

This module performs **measurements** on video encoding and decoding.
It also provides a detailed **dataset**.

It manages the following parameters:

#. It supports the ``libx264``, ``libx265``, ``libvpx-vp9``, ``libsvtav1`` and ``vvc`` encoders.
#. Distortions are measured using the ``lpips``, ``psnr``, ``ssim`` and ``vmaf`` metrics.
#. Encoding efforts are ``fast``, ``medium`` and ``slow``.
#. It takes care about the colorspaces.
#. Iterate over different ``effort``, ``encoder``, ``quality``, ``threads``, ``fps``, ``resolution`` and ``pix_fmt``.
#. Energy measurements are catched with ``RAPL`` and an external wattmeter on ``grid'5000``.
#. Get the ``cpu`` and ``ram`` activity.
#. Get a full environment context, including harware and software version.


Pipeline
========

.. ifconfig:: on_rtd

    .. image:: /_static/media/pipeline.svg
        :alt: Pipeline diagram

.. ifconfig:: not on_rtd

    .. image:: https://mendevi.readthedocs.io/latest/_images/pipeline.svg
        :alt: Pipeline diagram


Alternatives
============

#. The `MVCD database <https://github.com/cd-athena/MVCD>`_ also includes video encoding and decoding energy measurements.
#. The `COCONUT database <https://github.com/cd-athena/COCONUT>`_ also includes video decoding measurements.
