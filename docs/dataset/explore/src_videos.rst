.. _src_videos_dataset:

Accurately characterize the test videos
=======================================

Characterize the reference videos from the `CTC JVET <https://dash-large-files.akamaized.net/WAVE/3GPP/5GVideo/ReferenceSequences/>`_,
`Inter4k <https://alexandrosstergiou.github.io/datasets/Inter4K/index.html>`_ and `Big Buck Bunny <https://media.xiph.org/>`_.

Download
--------

Source videos
^^^^^^^^^^^^^

You can access the **uhd4k lossless** encoded source **videos** via the following torrents:

* `bbb.mp4 <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/video/bbb.mp4.torrent?inline=false>`_ (101 Go).
* `ctc <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/video/ctc.torrent?inline=false>`_ (140 Go).
* `inter4K <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/video/inter4k.torrent?inline=false>`_ (16 Go).

All information relating to copyright, sources and content can be found directly in the video metadata.
You can view this by using ``ffprobe``.

Database
^^^^^^^^

.. code:: shell

    mendevi download src_videos.db.xz.torrent

* `src_videos.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/src_videos.json.xz?inline=false>`_ (127 Ko).
* `src_videos.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/src_videos.db.xz.torrent?inline=false>`_ (144 Mo).

Statistical Properties
----------------------

Complexity
^^^^^^^^^^

To understand the nature of each test video. A similar plot has been made in `UHD Video Encoding in CPU Versus GPU: Quality and Performance Trade-Offs <https://ieeexplore.ieee.org/document/10937033>`_.

.. code:: shell

    mendevi plot src_videos.db -x rms_time_diff -y rms_sobel -c ref_stem -m profile -s 'ref_stem=' ''

.. image:: /_static/media/ctc_complexity.svg
    :alt: Energy per frame as a function of the number of frames during encoding

Reproduce
---------

for video in *.mkv; do
    for profile in sd hd fhd uhd4k; do
        echo "$video $profile"
    done
done | parallel -j 6 --colsep ' ' 'mendevi prepare {1} -p {2}'

.. code:: shell

    for video in {1..1000}.mp4; do
        for profile in sd hd fhd; do
            mendevi prepare $video -p $profile
        done
    done
    for video in *.mkv bbb.mp4; do
        for profile in sd hd fhd uhd4k; do
            mendevi prepare $video -p $profile
        done
    done
    mendevi probe --uvq reference* -d src_videos.db
