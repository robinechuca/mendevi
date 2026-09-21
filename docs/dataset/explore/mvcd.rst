.. _mvcd_datset:

Reproduction of MVCD
====================

This database attempts to replicate the `MVCD <https://github.com/cd-athena/MVCD>`_ measurements.

.. list-table:: The parameters of this database
    :header-rows: 1

    * - Name
      - Value
      - Description (link)
      - Total
    * - video
      - ``inter4k``
      - `ctc <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/video/inter4k.torrent?inline=false>`_
      - :math:`1000`
    * - profile
      - ``4k``
      - Same as source
      - :math:`1`
    * - resolution
      - ``3840x2160``, ``1920x1080``, ``1280x720``, ``960x540``
      - On fly
      - :math:`4`
    * - encoder
      - ``vvc``, ``libsvtav1``, ``libx264``, ``libx265``
      - :ref:`enc_encoder`
      - :math:`4`
    * - quality
      - :math:`\left\{\frac{k}{5} \mid k \in [1,4] \right\}`
      - :ref:`enc_quality`
      - :math:`4`
    * - effort
      - ``fast``, ``medium``
      - :ref:`enc_effort`
      - :math:`2`
    * - framerate
      - ``30``, ``60``
      - On fly
      - :math:`2`
    * - mode (à discuter)
      - ``vbr``
      - :ref:`enc_mode`
      - :math:`1`
    * - thread
      - :math:`\left\{ 8 \right\}`
      - :ref:`enc_threads`
      - :math:`1`


Reproduce
---------

.. code:: shell

    mendevi encode \
        --resolution 2160 3840 --resolution 1080 1920 --resolution 720 1280 --resolution 540 960 \
        --fps 60 --fps 30 \
        -c vvc -c libsvtav1 -c libx264 -c libx265 \
        -n4 -e fast -e medium \
        {1..1000}.mp4
