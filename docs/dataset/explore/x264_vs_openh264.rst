.. _x264_vs_openh264_dataset:

libx264 vs libopenh264 Dataset
==============================

Compare the **libx264** and the **libopenh264** encoders.

.. list-table:: The parameters of this database
    :header-rows: 1

    * - Name
      - Value
      - Description (link)
      - Total
    * - video
      - ``aov``, ``baolei_balloon``, ``baolei_man``, ``baolei_woman``, ``baolei_yard``, ``boat``, ``bode_museum``, ``brest_sedof``, ``cosmos``, ``cs_go``, ``elevator``, ``fountain``, ``graphics_mix_simple``, ``graphics_mix_transitions``, ``heroes_of_the_storm``, ``jianling_beach``, ``jianling_temple``, ``life_untouched``, ``meridian``, ``mine_craft``, ``mission_control``, ``mooving_text``, ``neon``, ``neptune_fountain_2``, ``neptune_fountain_3``, ``nocturne``, ``oberbaum_spree``, ``park_joy``, ``project_cars``, ``quadriga_tree``, ``rain_fruits``, ``riverbank``, ``skater``, ``soccer``, ``sol_levante``, ``sparks``, ``star_craft``, ``subway_tree``, ``text_mix_transition``, ``tiergarten_parkway``, ``tunnel_flag world_of_warcraft``
      - `ctc <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/video/ctc.torrent?inline=false>`_
      - :math:`42`
    * - profile
      - ``sd``, ``fhd``
      - `video resolution and more <https://gitlab.inria.fr/rrichard/mendevi/-/blob/main/mendevi/cst/profiles.py>`_
      - :math:`2`
    * - encoder
      - ``libx264``, ``libopenh264``
      - :ref:`enc_encoder`
      - :math:`2`
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
      - :math:`32256`

Download
--------

.. code:: shell

    mendevi download x264_vs_openh264.db.xz.torrent

* `x264_vs_openh264.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/x264_vs_openh264.json.xz?inline=false>`_ (18.3 Mo).
* `x264_vs_openh264.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/x264_vs_openh264.db.xz.torrent?inline=false>`_ (7.1 Go).

Plots
-----

Distortion and Consumption as a function of bitrate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Overall trend for all measures:

.. code:: shell

    mendevi plot x264_vs_openh264.db -x rate -y psnr -y vmaf -wx category -c '(encoder, profile)' -m effort

.. image:: /_static/media/x264_vs_openh264_bdr.svg
    :alt: Distortion as a function of bitrate

Result for a single video, including energy:

.. code:: shell

    mendevi plot x264_vs_openh264.db -x rate -x energy -y psnr -c encoder -m effort -wy profile -f "ref_stem=='park_joy'"

.. image:: /_static/media/x264_vs_openh264_cut.svg
    :alt: Link between distortion and energy for each encoder


Compression efficiency for PSNR=35dB
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot x264_vs_openh264.db -x rate -y energy -c '(encoder, profile)' -m category -f '34.5<psnr<35.5'

.. image:: /_static/media/x264_vs_openh264_efficiency_psnr.svg
    :alt: Consumption as a function of bitrate for a psnr of 35dB

Compression efficiency for rate=2Mb/s
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot x264_vs_openh264.db -x psnr -y energy -c '(encoder, profile)' -m category -f '1.8e6<rate<2.2e6'

.. image:: /_static/media/x264_vs_openh264_efficiency_rate.svg
    :alt: Consumption as a function of bitrate for a bitrate of 2Mb/s

Compression efficiency for fixed energy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot x264_vs_openh264.db -x rate -y psnr -wx 'round(energy/nbr_frames, 1)' -c encoder -m '(profile, effort)' -f "0.58<energy/nbr_frames<0.62 or 3.95<energy/nbr_frames<4.05"

.. image:: /_static/media/x264_vs_openh264_efficiency_energy.svg
    :alt: Consumption as a function of bitrate for a fixed energy

Conclusion
----------

* The **main consumption factor is the resolution**, not the encoder.
* At equal resolution and quality, ``libopenh264`` consumes less energy than ``libx264``.
* ``libx264`` **has a large variance in energy consumption** depending on the preset and the video content. It is therefore much less predictable than ``libopenh264``.

Ressources
^^^^^^^^^^

`this paper <https://iopscience.iop.org/article/10.1088/1757-899X/1172/1/012036/pdf>`_ (Performance comparison among popular
implementations of H.264 encoders) compare the distortion of that codecs.

Reproduce
---------

.. code:: shell

    for video in ctc/*.mkv; do
        mendevi prepare $video -p sd
        mendevi prepare $video -p fhd
    done
    mendevi encode -e fast -e medium -e slow -m cbr -m vbr -c libx264 -c libopenh264 reference*
    mendevi probe --psnr --ssim --vif --vmaf sample*
