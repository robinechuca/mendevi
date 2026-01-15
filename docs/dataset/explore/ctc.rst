.. _ctc_dataset:

Common Test Condition (JVET) Dataset
====================================

Characterize the reference videos from the `CTC JVET <https://dash-large-files.akamaized.net/WAVE/3GPP/5GVideo/ReferenceSequences/>`_.

Download
--------

.. code:: shell

    mendevi download ctc.db.xz.torrent

* `ctc.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ctc.json.xz?inline=false>`_ (127 Ko).
* `ctc.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ctc.db.xz.torrent?inline=false>`_ (137 Mo).

Statistical Properties
----------------------

Complexity
^^^^^^^^^^

To understand the nature of each test video. A similar plot has been made in `UHD Video Encoding in CPU Versus GPU: Quality and Performance Trade-Offs <https://ieeexplore.ieee.org/document/10937033>`_.

.. code:: shell

    mendevi plot '<ctc.db>' -x rms_time_diff -y rms_sobel -c ref_name -m profile

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
    mendevi probe reference*
    mendevi decode reference*
