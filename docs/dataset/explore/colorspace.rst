.. _colorspace_dataset:

Colorspace Dataset
==================

Allows you to see the impact of the color space on compression.

Download
--------

.. code:: shell

    mendevi download colorspace.db.xz.torrent

* `colorspace.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/colorspace.json.xz?inline=false>`_ (0 Mo).
* `colorspace.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/colorspace.db.xz.torrent?inline=false>`_ (0 Go).

Plots
-----

Distortion as a function of bitrate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<colorspace.db>' -x rate -y psnr -c transfer -m '(primaries, range)' -f 'codec!="ffv1" and name=="park_joy"'

.. image:: /_static/media/colorspace_bdr.svg
    :alt: Distortion as a function of bitrate

Reproduce
---------

.. code:: shell

    mendevi prepare park_joy.mp4 -p fhd
    mendevi prepare park_joy.mp4 -p fhd --primaries bt709 --transfer gamma22 --range tv
    mendevi prepare park_joy.mp4 -p fhd --primaries bt709 --transfer gamma22 --range pc
    mendevi prepare park_joy.mp4 -p fhd --primaries bt709 --transfer bt709 --range tv
    mendevi prepare park_joy.mp4 -p fhd --primaries bt709 --transfer bt709 --range pc
    mendevi prepare park_joy.mp4 -p fhd --primaries bt709 --transfer smpte2084 --range tv
    mendevi prepare park_joy.mp4 -p fhd --primaries bt709 --transfer smpte2084 --range pc
    mendevi prepare park_joy.mp4 -p fhd --primaries bt2020 --transfer gamma22 --range tv
    mendevi prepare park_joy.mp4 -p fhd --primaries bt2020 --transfer gamma22 --range pc
    mendevi prepare park_joy.mp4 -p fhd --primaries bt2020 --transfer bt709 --range tv
    mendevi prepare park_joy.mp4 -p fhd --primaries bt2020 --transfer bt709 --range pc
    mendevi prepare park_joy.mp4 -p fhd --primaries bt2020 --transfer smpte2084 --range tv
    mendevi prepare park_joy.mp4 -p fhd --primaries bt2020 --transfer smpte2084 --range pc

    mendevi encode -r 1 -c libx264 -c libsvtav1 --vbr 0 -n 2 reference*
    mendevi probe --ref reference_park_joy_fhd.mp4 reference* sample*
