.. _measure:

Perform Measures
================

The measurement process consists of four steps.

Preparation
-----------

This step allows you to prepare the ``Reference`` video from the ``Input`` video, to ensure that the rest of the process runs well.

This step specifically ensures the reference video:

* is encoded with the lossless **ffv1** codec
* has **square pixels** (1:1 ratio)
* is encoded in the **correct colour space** with consistent associated metadata
* is encoded at standard **resolution** and **framerate**
* is in 8-bit or 10-bit **YUV** pixel format
* is perfectly resized without distortion or aliasing

.. image:: /_static/media/prepare.avif
    :alt: mendevi prepare -p hd bbb.webm

Encode
------

This phase consists of transcoding the reference video in many different ways and measuring the machine's activity during this encoding process.

.. image:: /_static/media/encode.avif
    :alt: mendevi encode reference*

Probe
-----

This phase calculates the various metrics and properties of a transcoded video.

.. image:: /_static/media/probe.avif
    :alt: mendevi probe sample*

Decode
------

This phase consists of measuring the machine's activity during video decoding.

.. image:: /_static/media/decode.avif
    :alt: mendevi decode reference* sample*
