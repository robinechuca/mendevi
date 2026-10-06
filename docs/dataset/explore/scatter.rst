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
      - ``libx264``, ``h264_vaapi``, ``h264_nvenc``, ``libx265``, ``hevc_nvenc``, ``vvc``, ``libaom-av1``, ``libsvtav1``, ``libvpx-vp9``, ``av1_nvenc``
      - :ref:`enc_encoder`
      - :math:`10`
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

Plots
-----

Distortion and Consumption as a function of bitrate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Result for a single video, including energy:

.. code:: shell

    mendevi plot scatter.db -x rate -x energy_per_frame -y psnr -c encoder -m effort -wy profile -t t_enc_encode -f "ref_stem in {'boat', 'park_joy', 'cosmos'} and 'paradoxe-32' in hostname and profile in {'hd', 'uhd4k'}"

    mendevi plot scatter.db \
        -x rate -x energy_per_frame -y psnr -wy profile \
        -c encoder -m effort \
        -a "lamb < (rms_sobel*rms_time_diff/.1)**.5 < lamb + 0.1" \
        -f "'paradoxe-32' in hostname and profile in {'hd', 'uhd4k'}" \
        -t t_enc_encode

Bitrate Distortion
^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot scatter.db \
        -x rate -y vmaf -wx encoder -wy ref_stem \
        -c effort -m profile \
        -f "encoder in {'libsvtav1', 'av1_nvenc', 'libx264', 'h264_nvenc'} and ref_stem in {'baolei_balloon', 'park_joy'}" \
        -t t_enc_encode \
        -s "sharex=.*," 'sharex="all",'

.. image:: /_static/media/scatter_bdr.svg
    :alt: Bitrate distortion of a few codecs

Decoding energy according to the codec
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This plot shows the energy required to decode videos based on the codec and profile.
Only one machine is selected to make the data easier to read, but the trend remains the same on the other machines.

.. code:: shell

    mendevi plot scatter.db \
        -x rate -y energy_per_frame -wx profile \
        -c decoder  -t t_dec_decode \
        -a "lamb < (rms_sobel*rms_time_diff/.1)**.5 < lamb + 0.03" \
        -f "'paradoxe-32' in hostname and profile in {'hd', 'uhd4k'}"

.. video:: /_static/media/scatter_decode.webm
    :alt: Average decoding energy according to the codec and profile
    :width: 100%

Video complexity
^^^^^^^^^^^^^^^^

This figure helps clarify the relationship between spatial and temporal complexity.

.. code:: shell

    mendevi plot scatter.db -x rms_sobel -y rms_time_diff -c profile -m codec
    mendevi plot scatter.db -x spatial_dct -y temporal_dct -c profile -m codec

.. image:: /_static/media/scatter_rms.svg
    :alt: Link between spatial and temporal complexity (basic metric)

.. image:: /_static/media/scatter_dct.svg
    :alt: Link between spatial and temporal complexity (dct metrics)

* The classic ``SITI`` complexities are linked in a nearly linear way. As a result, they provide nearly the same information. In other words, they are redundant.

* The complexities based on ``DCT`` are less closely related. Both of them provide new information.

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
