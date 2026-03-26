.. _svtav1_vs_rav1e_vs_aom_dataset:

libsvtav1 vs librav1e vs libaom-av1 Dataset
===========================================

Compare the **libsvtav1**, **librav1e** and **libaom-av1** encoders.

.. list-table:: The parameters of this database
    :header-rows: 1

    * - Name
      - Value
      - Description (link)
      - Total
    * - video
      - ``aov``, ``baolei_balloon``, ``baolei_man``, ``baolei_woman``, ``baolei_yard``, ``boat``, ``bode_museum``, ``brest_sedof``, ``cosmos``, ``cs_go``, ``elevator``, ``fountain``, ``graphics_mix_simple``, ``graphics_mix_transitions``, ``heroes_of_the_storm``, ``jianling_beach``, ``jianling_temple``, ``life_untouched``, ``meridian``, ``mine_craft``, ``mission_control``, ``mooving_text``, ``neon``, ``neptune_fountain_2``, ``neptune_fountain_3``, ``nocturne``, ``oberbaum_spree``, ``park_joy``, ``project_cars``, ``quadriga_tree``, ``rain_fruits``, ``riverbank``, ``skater``, ``soccer``, ``sol_levante``, ``sparks``, ``star_craft``, ``subway_tree``, ``text_mix_transition``, ``tiergarten_parkway``, ``tunnel_flag world_of_warcraft``
      - `ctc <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/video/ctc.torrent?inline=false>`_
      - :math:`42`
    * - profile
      - ``sd``, ``fhd``
      - `video resolution and more <https://gitlab.inria.fr/rrichard/mendevi/-/blob/main/mendevi/cst/profiles.py>`_
      - :math:`2`
    * - encoder
      - ``libsvtav1``, ``librav1e``, ``libaom-av1``
      - :ref:`enc_encoder`
      - :math:`3`
    * - quality
      - :math:`\left\{\frac{k}{17} \mid k \in [1,16] \right\}`
      - :ref:`enc_quality`
      - :math:`16`
    * - effort
      - ``fast``, ``medium``, ``slow``
      - :ref:`enc_effort`
      - :math:`3`
    * - mode
      - ``cbr``, ``vbr``
      - :ref:`enc_mode`
      - :math:`2`
    * - thread
      - :math:`\left\{ 8 \right\}`
      - :ref:`enc_threads`
      - :math:`1`
    * - repeat
      - :math:`2` times
      - total repetitions
      - :math:`2`
    * - ramdisk
      - ``yes``
      - shm in :ref:`enc_cmd`
      - :math:`1`
    * - host
      - ``paradoxe-32``
      - :ref:`env_hostname`
      - :math:`1`
    * - metrics
      - ``psnr``, ``ssim``, ``vif``, ``vmaf``
      - :ref:`t_met_metric`
      -
    * - **total**
      - :math:`\prod`
      - total number of points
      - :math:`9197/48384`

Download
--------

.. code:: shell

    mendevi download svtav1_vs_rav1e_vs_aom.db.xz.torrent

* `svtav1_vs_rav1e_vs_aom.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/svtav1_vs_rav1e_vs_aom.json.xz?inline=false>`_ (6.9 Mo).
* `svtav1_vs_rav1e_vs_aom.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/svtav1_vs_rav1e_vs_aom.db.xz.torrent?inline=false>`_ (24.9 Go).

Plots
-----

Distortion and Consumption as a function of bitrate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Overall trend for all measures:

.. code:: shell

    mendevi plot svtav1_vs_rav1e_vs_aom.db -x rate -y psnr -y vmaf -wx category -c '(encoder, profile)' -m effort

.. image:: /_static/media/svtav1_vs_rav1e_vs_aom_bdr.svg
    :alt: Distortion as a function of bitrate

Result for a single video, including energy:

.. code:: shell

    mendevi plot svtav1_vs_rav1e_vs_aom.db -x rate -x energy -y psnr -c encoder -m effort -wy profile -f "ref_stem=='park_joy'"

.. image:: /_static/media/svtav1_vs_rav1e_vs_aom_cut.svg
    :alt: Link between distortion and energy for each encoder


Conclusion
----------

#. libvstav1 is significantly faster than librav1e! This difference is even more pronounced at higher throughput rates.
#. librav1e allows for lower bitrate (in constant quality mode).
#. Although librav1e shows better distortion at high bitrates, **libsvtav1 is better** at equal encoding duration.

Reproduce
---------

.. code:: shell

    mkdir av1
    for video in ctc/*.mkv; do
        mendevi prepare $video -o av1 -p sd
        mendevi prepare $video -o av1 -p fhd
    done
    cd av1
    mendevi encode -e fast -e medium -e slow -m cbr -m vbr -c libsvtav1 -c librav1e -c libaom-av1 reference*
    mendevi probe --psnr --ssim --vif --vmaf reference* sample*
