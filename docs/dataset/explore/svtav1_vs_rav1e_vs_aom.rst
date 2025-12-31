.. _svtav1_vs_rav1e_vs_aom_dataset:

libsvtav1 vs librav1e vs libaom-av1 Dataset
===========================================

Compare the **libsvtav1**, **librav1e** and **libaom-av1** encoders.

Download
--------

.. code:: shell

    mendevi download svtav1_vs_rav1e_vs_aom.db.xz.torrent

* `svtav1_vs_rav1e_vs_aom.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/svtav1_vs_rav1e_vs_aom.json.xz?inline=false>`_ (62.7 Ko).
* `svtav1_vs_rav1e_vs_aom.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/svtav1_vs_rav1e_vs_aom.db.xz.torrent?inline=false>`_ (0 Go).

Plots
-----

Distortion as a function of bitrate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<svtav1_vs_rav1e_vs_aom.db>' -x rate -y psnr -y vmaf -wx category -c '(encoder, profile)' -m effort

.. image:: /_static/media/svtav1_vs_rav1e_vs_aom_bdr.svg
    :alt: Distortion as a function of bitrate

Conclusion
----------

#. libvstav1 is significantly faster than librav1e! This difference is even more pronounced at higher throughput rates.
#. librav1e allows for lower bitrate (in constant quality mode).
#. Although librav1e shows better distortion at high bitrates, **libsvtav1 is better** at equal encoding duration.

Reproduce
---------

.. code:: shell

    for video in ctc/*.mkv; do
        mendevi prepare $video -p sd
        mendevi prepare $video -p fhd
    done
    mendevi encode reference* -e fast -e medium -e slow -m cbr -m vbr -c libsvtav1 -c librav1e -c libaom-av1
    mendevi probe sample_* --psnr --ssim --vif --vmaf
