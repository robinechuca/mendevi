.. _duration_dataset:

Duration Dataset
================

Allows you to see the impact of video length on compression and energy consumption.

.. list-table:: The parameters of this database
    :header-rows: 1

    * - Name
      - Value
      - Description (link)
      - Total
    * - video
      - :math:`100` slices
      - `Big Buck Bunny <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/video/bbb.mp4.torrent?inline=false>`_
      - :math:`100`
    * - profile
      - ``sd``, ``fhd``
      - `video resolution and more <https://gitlab.inria.fr/rrichard/mendevi/-/blob/main/mendevi/cst/profiles.py>`_
      - :math:`2`
    * - encoder
      - ``libsvtav1``, ``libx264``
      - :ref:`enc_encoder`
      - :math:`2`
    * - quality
      - :math:`\left\{\frac{k}{3} \mid k \in [1,2] \right\}`
      - :ref:`enc_quality`
      - :math:`2`
    * - effort
      - ``fast``, ``medium``
      - :ref:`enc_effort`
      - :math:`2`
    * - mode
      - ``cbr``, ``vbr``
      - :ref:`enc_mode`
      - :math:`2`
    * - thread
      - :math:`\left\{ 8 \right\}`
      - :ref:`enc_threads`
      - :math:`1`
    * - repeat
      - :math:`10` times
      - total repetitions
      - :math:`10`
    * - host
      - ``paradoxe-32``, ``yeti-2``
      - :ref:`env_hostname`
      - :math:`2`
    * - **total**
      - :math:`\prod`
      - total number of points
      - :math:`27054`

Download
--------

.. code:: shell

    mendevi download duration.db.xz.torrent

* `duration.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/duration.json.xz?inline=false>`_ (24.3 Mo).
* `duration.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/duration.db.xz.torrent?inline=false>`_ (29.8 Go).

Plots
-----

Encoding energy per frame as a function of the number of frames
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot duration.db -x nbr_frames -y energy_per_frame -e ref_stem -c '(encoder, effort)' -wy profile -wx hostname -t t_enc_encode

.. image:: /_static/media/duration_energy_frames_enc.svg
    :alt: Energy per frame as a function of the number of frames during encoding

Decoding energy per frame as a function of the number of frames
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot duration.db -x nbr_frames -y energy_per_frame -e ref_stem -c '(codec, effort)' -wy profile -wx hostname -t t_dec_decode

.. image:: /_static/media/duration_energy_frames_dec.svg
    :alt: Energy per frame as a function of the number of frames during decoding

Bitrate as a function of the number of frame at constant quality
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot duration.db -x nbr_frames -y rate -c encoder -m effort -wx quality -wy profile -f "mode == 'vbr'"

.. image:: /_static/media/duration_rate_frames.svg
    :alt: Energy per frame as a function of the number of frames

Conclusion
----------

When the video contains enough images, the average energy per frame no longer depends on the duration of the video. Thus, for videos with more than 300 images, ie more than 10 seconds, this effect becomes negligible.

These results are consistent with the `UIT-R BT.500-15 (05/2023) <https://www.itu.int/rec/R-REC-BT.500-15-202305-I>`_ which recommends 10-second sequences.

Reproduce
---------

First, generate the video segments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The first step is to extract random length segments from a video.

The video used is ``bbb.mp4``, the length of the segments follows a base-10 exponential probability distribution.

Next, perform the measurements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi encode -r10 -c libx264 -c libsvtav1 -e fast -e medium -m cbr -m vbr -n2 reference*
    mendevi probe --no-vmaf reference* sample*
    mendevi decode -r10 sample*
