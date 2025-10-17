.. _duration_dataset:

Duration Dataset
================

Allows you to see the impact of video length on compression and energy consumption.

Download
--------

* `duration.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/duration.json.xz>`_ (6.4 Mo).
* `duration.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/duration.db.xz.torrent>`_ (0 Go).

Plots
-----

Energy per frame as a function of the number of frames
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot duration.db -x nbr_frames -y 'energy/nbr_frames' -c encoder -m effort -wx quality -wy profile


.. image:: /_static/media/duration_energy_frames.svg
    :alt: Energy per frame as a function of the number of frames


Bitrate as a function of the number of frame at constant quality
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot duration.db -x nbr_frames -y rate -c encoder -m effort -wx quality -wy profile -f 'mode == "vbr"'


.. image:: /_static/media/duration_rate_frames.svg
    :alt: Energy per frame as a function of the number of frames
