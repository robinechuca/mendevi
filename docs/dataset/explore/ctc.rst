.. _ctc_dataset:

Common Test Condition (JVET) Dataset
====================================

Characterize the reference videos from the `CTC JVET <https://dash-large-files.akamaized.net/WAVE/3GPP/5GVideo/ReferenceSequences/>`_.

Download
--------

Source videos
^^^^^^^^^^^^^

You can access the **uhd4k lossless** encoded source **videos** via the following torrents:

* `bbb.mp4 <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/video/bbb.mp4.torrent?inline=false>`_ (101 Go).
* `ctc <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/video/ctc.torrent?inline=false>`_ (140 Go).
* `inter4K <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/video/inter4k.torrent?inline=false>`_ (16 Go).

All information relating to copyright, sources and content can be found directly in the video metadata.
You can view this by typing ``ffprobe park_joy.mkv``.

Database
^^^^^^^^

.. code:: shell

    mendevi download ctc.db.xz.torrent

* `ctc.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ctc.json.xz?inline=false>`_ (127 Ko).
* `ctc.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ctc.db.xz.torrent?inline=false>`_ (144 Mo).

Statistical Properties
----------------------

Complexity
^^^^^^^^^^

To understand the nature of each test video. A similar plot has been made in `UHD Video Encoding in CPU Versus GPU: Quality and Performance Trade-Offs <https://ieeexplore.ieee.org/document/10937033>`_.

.. code:: shell

    mendevi plot ctc.db -x rms_time_diff -y rms_sobel -c ref_stem -m profile -s 'ref_stem=' ''

.. image:: /_static/media/ctc_complexity.svg
    :alt: Energy per frame as a function of the number of frames during encoding

Reproduce
---------

.. code:: shell

    for video in ctc/*.mkv; do
        for profile in sd hd fhd uhd4k; do
            mendevi prepare $video -p $profile
        done
    done
    mendevi probe --rms-sobel --rms-time-diff --spatial-dct --temporal-dct reference* -d ctc.db
