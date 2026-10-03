.. _scatter_dataset:

Scatter Dataset
===============

Corresponds to a random subsampling of a highly varied set of encoding scenarios.
The dataset contains 35777 encoding measurements and 112499 decoding measurements.

.. list-table:: The parameters of this database
    :header-rows: 1

    * - Name
      - Value
      - Description (link)
      - Total
    * - video
      - ``baolei_balloon``, ``baolei_yard``, ``boat``, ``bode_museum``, ``brest_sedof``, ``cosmos``, ``elevator``, ``fountain``, ``graphics_mix_simple``, ``graphics_mix_transitions``, ``life_untouched``, ``meridian``, ``mooving_text``, ``neon``, ``neptune_fountain_2``, ``neptune_fountain_3``, ``nocturne``, ``oberbaum_spree``, ``park_joy``, ``quadriga_tree``, ``rain_fruits``, ``riverbank``, ``skater``, ``soccer``, ``sol_levante``, ``sparks``, ``subway_tree``, ``text_mix_transition``, ``tiergarten_parkway``, ``tunnel_flag``
      - `ctc <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/video/ctc.torrent?inline=false>`_
      - :math:`30`
    * - profile
      - ``sd``, ``hd``, ``fhd``,  ``uhd4k``
      - `video resolution and more <https://gitlab.inria.fr/rrichard/mendevi/-/blob/main/mendevi/cst/profiles.py>`_
      - :math:`4`
    * - encoder
      - ``libx264``, ``h264_vaapi``, ``h264_nvenc``, ``libx265``, ``hevc_nvenc``, ``vvc``, ``libaom-av1``, ``libsvtav1``, ``av1_nvenc``
      - :ref:`enc_encoder`
      - :math:`9`
    * - quality
      - :math:`\left\{\frac{k}{25} \mid k \in [1,24] \right\}`
      - :ref:`enc_quality`
      - :math:`24`
    * - effort
      - ``fast``, ``medium``, ``slow``
      - :ref:`enc_effort`
      - :math:`3`
    * - mode
      - ``crf``
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
      - ``abacus26``, ``dahu``, ``gemini``, ``nova``, ``paradoxe``, ``pc-dell``, ``yeti``
      - :ref:`env_hostname`
      - :math:`7`
    * - metrics
      - ``psnr``, ``ssim``, ``vif``, ``vmaf``, ``lpips_alex``
      - :ref:`t_met_metric`
      -
    * - **total**
      - :math:`\le \prod`
      - total number of points
      - :math:`35777`


Download
--------

.. code:: shell

    mendevi download scatter.db.xz.torrent

* `scatter.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/scatter.json.xz?inline=false>`_ (53.7 Mo).
* `scatter.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/scatter.db.xz.torrent?inline=false>`_ (50.8 Go).


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
      -c av1_nvenc -c h264_nvenc -c hevc_nvenc -c libaom-av1 -c libsvtav1 -c libvpx-vp9 -c libx264 -c libx265 -c vvc \
      reference*
    mendevi decode -r2 reference*
    mendevi decode -r1 *.mp4
    mendevi probe --psnr --ssim --vmaf --vif --lpips-alex --rms-sobel --rms-time-diff --spatial-dct --temporal-dct *.mp4
