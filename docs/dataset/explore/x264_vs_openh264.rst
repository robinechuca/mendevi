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

    mendevi plot '<x264_vs_openh264.db>' -x rate -y psnr -y vmaf -wx category -c '(encoder, profile)' -m effort

.. image:: /_static/media/x264_vs_openh264_bdr.svg
    :alt: Distortion as a function of bitrate

Consomation as a function of bitrate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<x264_vs_openh264.db>' -x rate -y energy -wx category -wy profile -c encoder -m effort -f "category in {'4K-TV', 'Gaming'}"

.. image:: /_static/media/x264_vs_openh264_energy.svg
    :alt: Consomation as a function of bitrate

Compression efficiency for PSNR=35dB
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<x264_vs_openh264.db>' -x rate -y energy -c '(encoder, profile)' -m category -f '34<psnr<36'

.. image:: /_static/media/x264_vs_openh264_efficiency.svg
    :alt: Consomation as a function of bitrate for a psnr of 35dB

Conclusion
----------

No conclusion yet!

Reproduce
---------

.. code:: shell

    mendevi prepare -p fhd park_joy.mp4
    mendevi encode reference* -e fast -e medium -e slow -m cbr -m vbr -c libx264 -c libopenh264
    mendevi probe sample_* --psnr --ssim --vif --vmaf
