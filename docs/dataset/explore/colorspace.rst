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



mendevi plot mendevi.db -x rate -y psnr -c transfer -m '(primaries, range)' -f 'name=="park_joy" and codec != "ffv1"'
