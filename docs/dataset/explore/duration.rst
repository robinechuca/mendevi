.. _duration_dataset:

Duration Dataset
================

Allows you to see the impact of video length on compression and energy consumption.

Download
--------

.. code:: shell

    mendevi download duration.db.xz.torrent

* `duration.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/duration.json.xz?inline=false>`_ (7.6 Mo).
* `duration.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/duration.db.xz.torrent?inline=false>`_ (0 Go).

Plots
-----

Energy per frame as a function of the number of frames
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<duration.db>' -x nbr_frames -y energy_per_frame -e nbr_frames -c encoder -m effort -wx quality -wy profile

.. image:: /_static/media/duration_energy_frames.svg
    :alt: Energy per frame as a function of the number of frames

Bitrate as a function of the number of frame at constant quality
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<duration.db>' -x nbr_frames -y rate -e nbr_frames -c encoder -m effort -wx quality -wy profile -f 'mode == "vbr"'

.. image:: /_static/media/duration_rate_frames.svg
    :alt: Energy per frame as a function of the number of frames

Reproduce
---------

First, generate the video segments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The first step is to extract random length segments from a video.

The video used is ``bbb.mp4``, the length of the segments follows a base-10 exponential probability distribution.

Next, perform the measurements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi encode reference* -r 10 -c libx264 -c libsvtav1 -e fast -e medium -m cbr -m vbr -n 2
    mendevi probe reference* sample* --no-lpips-alex --no-lpips-vgg --no-uvq --no-vmaf
    mendevi decode sample* -r 10
