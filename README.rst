.. rst syntax: https://deusyss.developpez.com/tutoriels/Python/SphinxDoc/
.. version conv: https://peps.python.org/pep-0440/

**Me** sures d'**En** codage et **Dé** codage **Vi** déo.
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

.. image:: https://readthedocs.org/projects/cutcutcodec/badge/?version=latest
    :alt: [documentation]
    :target: https://mendevi.readthedocs.io

Useful links:
`Binary Installers <https://pypi.org/project/cutcutcodec>`_ |
`Source Repository <https://framagit.org/robinechuca/cutcutcodec>`_ |
`Online Documentation <https://cutcutcodec.readthedocs.io/stable>`_ |


Description
===========

This module performs **measurements** on video encoding and decoding.
It also provides a detailed **database**.

It manages the following parameters:

#. It supports the ``libx264``, ``libx265``, ``libvpx-vp9``, ``libsvtav1`` and ``vvc`` encoders.
#. Distortions are measured using the ``lpips``, ``psnr``, ``ssim`` and ``vmaf`` metrics.
#. Encoding efforts are ``fast``, ``medium`` and ``slow``.
#. Iterate over different ``threads``, ``quality (crf)``, ``effort``, ...
#. Energy measurements are catched with ``RAPL`` and an external wattmeter on ``Grid'5000``.
#. Get the ``cpu`` and ``ram`` activity.
#. Get a full environement context


Alternatives
============

#. The `MVCD database <https://github.com/cd-athena/MVCD>`_ also includes video encoding and decoding energy measurements.
#. The `COCONUT database <https://github.com/cd-athena/COCONUT>`_ also includes video decoding measurements.
