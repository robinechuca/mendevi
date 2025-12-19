.. _x264_vs_openh264_dataset:

libx264 vs libopenh264 Dataset
==============================

Compare the **libx264** and the **libopenh264** encoders.

Download
--------

.. code:: shell

    mendevi download x264_vs_openh264.db.xz.torrent

* `x264_vs_openh264.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/x264_vs_openh264.json.xz?inline=false>`_ (0 Ko).
* `x264_vs_openh264.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/x264_vs_openh264.db.xz.torrent?inline=false>`_ (0 Go).

Plots
-----

Distortion as a function of bitrate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<x264_vs_openh264.db>' -x rate -y psnr -y comp_ssim -wx category -c '(encoder, profile)' -m effort -f "not ref_name.isdigit()"

.. image:: /_static/media/x264_vs_openh264_bdr.svg
    :alt: Distortion as a function of bitrate
