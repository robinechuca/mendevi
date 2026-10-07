.. _crf_vs_cbr_vs_qp_dataset:

CRF vs CBR vs QP Dataset
========================

Compare the **CRF**, **CBR** and **QP** modes.

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
      - ``crf``, ``cbr``, ``qp``
      - :ref:`enc_mode`
      - :math:`3`
    * - thread
      - :math:`\left\{ 8 \right\}`
      - :ref:`enc_threads`
      - :math:`1`
    * - repeat
      - :math:`5` times
      - total repetitions
      - :math:`5`
    * - ramdisk
      - ``yes``
      - shm in :ref:`enc_cmd`
      - :math:`1`
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

Reproduce
---------

.. code:: shell

    mendevi prepare park_joy.mkv -p sd
    mendevi prepare park_joy.mkv -p fhd

    mendevi encode -r5 -m crf -m cbr -m qp -c libx264 -c libsvtav1 -e fast -e medium reference*
    mendevi decode -r5 sample*

    mendevi probe reference* sample*
