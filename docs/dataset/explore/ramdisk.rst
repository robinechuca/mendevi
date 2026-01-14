.. _ramdisk_dataset:

RAM Disk Dataset
================

Compare the performance of ffmpeg when video are read and written to **RAM**, and when they are read and written to the **hard drive**.

Download
--------

.. code:: shell

    mendevi download ramdisk.db.xz.torrent

* `ramdisk.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ramdisk.json.xz?inline=false>`_ (0 Ko).
* `ramdisk.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ramdisk.db.xz.torrent?inline=false>`_ (0 Go).

Reproduce
---------

.. code:: shell

    mendevi prepare park_joy.mkv -p sd
    mendevi prepare park_joy.mkv -p fhd

    mendevi encode -c libx264 -c libsvtav1 -e fast -e medium -t 8 -t 16 --ram yes -d ram_yes.db reference*
    mendevi encode -c libx264 -c libsvtav1 -e fast -e medium -t 8 -t 16 --ram no -d ram_no.db reference*
    mendevi merge ram_yes.db ram_no.db && mv merge_ram_yes_ram_no.db ramdisk.db && rm ram_*

    mendevi probe -d ramdisk.db reference*
    mendevi probe -d ramdisk.db sample* --no-psnr --no-ssim --no-vif --no-vmaf
