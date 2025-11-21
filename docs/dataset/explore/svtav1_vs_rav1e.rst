.. _svtav1_vs_rav1e_dataset:

libsvtav1 vs librav1e Dataset
=============================

Compare the **libsvtav1** and **librav1e** encoders.

Download
--------

.. code:: shell

    mendevi download svtav1_vs_rav1e.db.xz.torrent

* `svtav1_vs_rav1e.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/svtav1_vs_rav1e.json.xz?inline=false>`_ (62.7 Ko).
* `svtav1_vs_rav1e.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/svtav1_vs_rav1e.db.xz.torrent?inline=false>`_ (0 Go).

Plots
-----

Distortion as a function of bitrate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<svtav1_vs_rav1e.db>' -x rate -y psnr -y comp_ssim -c encoder -m effort

.. image:: /_static/media/svtav1_vs_rav1e_bdr.svg
    :alt: Distortion as a function of bitrate

Encoding duration
^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<svtav1_vs_rav1e.db>' -x rate -y act_duration -c encoder -m effort

.. image:: /_static/media/svtav1_vs_rav1e_enc_duration.svg
    :alt: Encoding duration

Conclusion
----------

* libvstav1 is significantly faster than librav1e! This difference is even more pronounced at higher throughput rates. speed(librav1e) > speed(libsvtav1).
* librav1e allows for lower bitrate (in constant quality mode).
* Although librav1e shows better distortion at high bitrates, **libsvtav1 is better** at equal encoding duration.

Reproduce
---------

.. code:: shell

    mendevi prepare -p fhd park_joy.mp4
    mendevi encode reference_park_joy_fhd.mp4 -c libsvtav1 -c librav1e -m vbr -e fast -e medium -e slow -r 1
    mendevi probe sample_* --no-vmaf
