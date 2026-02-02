.. _ramdisk_dataset:

RAM Disk Dataset
================

Compare the performance of ffmpeg when videos are read and written to **RAM**, and when they are read and written to the **hard drive**.

Download
--------

.. code:: shell

    mendevi download ramdisk.db.xz.torrent

* `ramdisk.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ramdisk.json.xz?inline=false>`_ (481 Ko).
* `ramdisk.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ramdisk.db.xz.torrent?inline=false>`_ (305 Mo).

Plots
-----

Effect on encoding
^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot ramdisk.db -x rate -y energy -c enc_ram -wx profile -e enc_scenario -s 'sharey="row"' 'sharey=False'

.. image:: /_static/media/ramdisk_encode.svg
    :alt: Variation of encoding energy depending of device.

Effect on decoding
^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot ramdisk.db -x rate -y energy -c dec_ram -wx profile -e dec_scenario -s 'sharey="row"' 'sharey=False'

.. image:: /_static/media/ramdisk_decode.svg
    :alt: Variation of decoding energy depending of device.

Conclusion
----------

The energy and time required to encode and decode a video **does not depend** on whether it is read and written from and to an SSD or in RAM.

Reproduce
---------

.. code:: shell

    mendevi prepare park_joy.mkv -p sd
    mendevi prepare park_joy.mkv -p fhd

    mendevi encode -r5 -c libx264 -c libsvtav1 -e fast -e medium -t8 -t16 --ram yes -d ram_yes.db reference*
    mendevi encode -r5 -c libx264 -c libsvtav1 -e fast -e medium -t8 -t16 --ram no -d ram_no.db reference*
    mendevi decode -r5 --family cpu --ram yes -d ram_yes.db sample*
    mendevi decode -r5 --family cpu --ram no -d ram_no.db sample*
    mendevi merge ram_yes.db ram_no.db && mv merge_ram_yes_ram_no.db ramdisk.db

    mendevi probe --no-psnr --no-ssim --no-vif --no-vmaf -d ramdisk.db reference* sample*
