.. _ramdisk_dataset:

RAM Disk Dataset
================

Compare the performance of ffmpeg when videos are read and written to **RAM**, and when they are read and written to the **hard drive**.

.. notes::

  Tracer l'historgame des differences.

.. list-table:: The parameters of this database
    :header-rows: 1

    * - Name
      - Value
      - Description (link)
      - Total
    * - video
      - ``park_joy``
      - `ctc <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/video/ctc.torrent?inline=false>`_
      - :math:`1`
    * - profile
      - ``sd``, ``fhd``
      - `video resolution and more <https://gitlab.inria.fr/rrichard/mendevi/-/blob/main/mendevi/cst/profiles.py>`_
      - :math:`2`
    * - encoder
      - ``libsvtav1``, ``libx264``
      - :ref:`enc_encoder`
      - :math:`2`
    * - quality
      - :math:`\left\{\frac{k}{17} \mid k \in [1,16] \right\}`
      - :ref:`enc_quality`
      - :math:`16`
    * - effort
      - ``fast``, ``medium``
      - :ref:`enc_effort`
      - :math:`2`
    * - mode
      - ``vbr``
      - :ref:`enc_mode`
      - :math:`1`
    * - thread
      - :math:`\left\{ 8 \right\}`
      - :ref:`enc_threads`
      - :math:`1`
    * - repeat
      - :math:`5` times
      - total repetitions
      - :math:`5`
    * - ramdisk
      - ``yes``, ``no``
      - shm in :ref:`enc_cmd`
      - :math:`2`
    * - host
      - ``paradoxe-26``
      - :ref:`env_hostname`
      - :math:`1`
    * - metrics
      -
      - :ref:`t_met_metric`
      -
    * - **total**
      - :math:`\prod`
      - total number of points
      - :math:`2560`

Download
--------

.. code:: shell

    mendevi download ramdisk.db.xz.torrent

* `ramdisk.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ramdisk.json.xz?inline=false>`_ (481 Ko).
* `ramdisk.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/ramdisk.db.xz.torrent?inline=false>`_ (320 Mo).

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
