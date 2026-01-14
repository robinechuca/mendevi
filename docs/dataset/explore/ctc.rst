.. _ctc_dataset:

Common Test Condition (JVET) Dataset
====================================

Characterize the reference videos from the `CTC JVET <https://dash-large-files.akamaized.net/WAVE/3GPP/5GVideo/ReferenceSequences/>`_.

Download
--------

.. code:: shell

    mendevi download ctc.db.xz.torrent

* `ctc.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ctc.json.xz?inline=false>`_ (0 Ko).
* `ctc.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ctc.db.xz.torrent?inline=false>`_ (0 Go).

Reproduce
---------

.. code:: shell

    for video in ctc/*.mkv; do
        for profile in sh hd fhd uhd4k; do
            mendevi prepare $video -p $profile
        done
    done
    mendevi probe reference*
    mendevi decode
