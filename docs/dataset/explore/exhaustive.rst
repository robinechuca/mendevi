.. _exhaustiev_dataset:

Full Dataset
============

Corresponds to a random subsampling of a highly varied set of encoding scenarios.

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
      - ``sd``, ``hd``, ``fhd``,  ``uhd4k``
      - `video resolution and more <https://gitlab.inria.fr/rrichard/mendevi/-/blob/main/mendevi/cst/profiles.py>`_
      - :math:`4`
    * - encoder
      - ``av1_nvenc``, ``h264_nvenc``, ``hevc_nvenc``, ``libaom-av1``, ``libsvtav1``, ``libx264``, ``libx265``, ``vvc``
      - :ref:`enc_encoder`
      - :math:`8`
    * - quality
      - :math:`\left\{\frac{k}{25} \mid k \in [1,24] \right\}`
      - :ref:`enc_quality`
      - :math:`24`
    * - effort
      - ``fast``, ``medium``, ``slow``
      - :ref:`enc_effort`
      - :math:`3`
    * - mode
      - ``vbr``
      - :ref:`enc_mode`
      - :math:`1`
    * - thread
      - :math:`\left\{ 8 \right\}`
      - :ref:`enc_threads`
      - :math:`1`
    * - repeat
      - :math:`1` times
      - total repetitions
      - :math:`1`
    * - ramdisk
      - ``yes``
      - shm in :ref:`enc_cmd`
      - :math:`1`
    * - host
      - ``paradoxe``, ``yeti``, ``abacus26``, ``pc-intel``
      - :ref:`env_hostname`
      - :math:`3`
    * - metrics
      - ``psnr``, ``ssim``, ``vif``, ``vmaf``, ``lpips_alex``
      - :ref:`t_met_metric`
      -
    * - **total**
      - :math:`\prod`
      - total number of points
      - :math:`387072`

Reproduce
---------

.. code:: shell

    for video in ctc/*.mkv; do
        for profile in sd hd fhd uhd4k; do
          mendevi prepare $video -p $profile
        done
    done
    mendevi encode -r1 \
      -n 24 \
      -e fast -e medium -e slow \
      -m cbr -m vbr \
      -c av1_nvenc -c h264_nvenc -c hevc_nvenc -c libaom-av1 -c libsvtav1 -c libvpx-vp9 -c libx264 -c libx265 -c vvc \
      -t 4 -t 8 \
      reference*
    mendevi decode -r2 reference*
    mendevi probe --psnr --ssim --vif --vmaf --lpips-alex sample*
