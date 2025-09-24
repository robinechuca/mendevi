.. _measure:

Perform Measures
================

The measurement process consists of four steps:

1) **Preparation**: This phase allows you to generate a "perfect" raw video file, in the sense that it contains all the metadata necessary for the next steps.

.. image:: https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/docs/media/prepare.avif
    :alt: mendevi prepare -p hd bbb.webm

2) **Encode**: This phase consists of transcoding the reference video in many different ways and measuring the machine's activity during this encoding process.

.. image:: https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/docs/media/encode.avif
    :alt: mendevi encode reference*

3) **Probe**: This phase calculates the various metrics and properties of a transcoded video.

.. image:: https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/docs/media/probe.avif
    :alt: mendevi probe sample*

4) **Decode**: This phase consists of measuring the machine's activity during video decoding.

.. image:: https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/docs/media/decode.avif
    :alt: mendevi decode reference* sample*
    