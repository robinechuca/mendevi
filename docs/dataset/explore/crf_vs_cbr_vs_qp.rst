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
    * - effort
      - ``fast``, ``medium``
      - :ref:`enc_effort`
      - :math:`2`
    * - encoder
      - ``libsvtav1``, ``libx264``, ``libx265``
      - :ref:`enc_encoder`
      - :math:`2`
    * - host
      - ``paradoxe-26``
      - :ref:`env_hostname`
      - :math:`1`
    * - metrics
      - ``psnr``, ``ssim``
      - :ref:`t_met_metric`
      -
    * - mode
      - ``crf``, ``cbr``, ``qp``
      - :ref:`enc_mode`
      - :math:`3`
    * - profile
      - ``sd``, ``fhd``
      - `video resolution and more <https://gitlab.inria.fr/rrichard/mendevi/-/blob/main/mendevi/cst/profiles.py>`_
      - :math:`2`
    * - quality
      - :math:`\left\{\frac{k}{17} \mid k \in [1,16] \right\}`
      - :ref:`enc_quality`
      - :math:`16`
    * - repeat
      - :math:`5` times
      - total repetitions
      - :math:`5`
    * - video
      - ``baolei_balloon``, ``park_joy``
      - `ctc <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/video/ctc.torrent?inline=false>`_
      - :math:`2`
    * - **total**
      - :math:`\prod`
      - total number of points
      - :math:`5760`

Download
--------

.. code:: shell

    mendevi download crf_vs_cbr_vs_qp.db.xz.torrent

* `crf_vs_cbr_vs_qp.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/crf_vs_cbr_vs_qp.json.xz?inline=false>`_ (914 Ko).
* `crf_vs_cbr_vs_qp.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/crf_vs_cbr_vs_qp.db.xz.torrent?inline=false>`_ (593 Mo).

Plots
-----

Effect of mode on energy
^^^^^^^^^^^^^^^^^^^^^^^^

The graph below shows the energy impact of the QP for a comparable bitrate.

.. code:: shell

    mendevi plot crf_vs_cbr_vs_qp.db -x bitrate -y energy -wx profile -wy encoder -c mode -m effort -e quality

.. image:: /_static/media/crf_vs_cbr_vs_qp_energy_bitrate.svg
    :alt: Effect of mode on energy at constant bitrate

The graph below shows the energy impact of the QP for a comparable quality.

.. code:: shell

    mendevi plot crf_vs_cbr_vs_qp.db -x psnr -y energy -wx profile -wy encoder -c mode -m effort -e quality -t t_enc_encode

.. image:: /_static/media/crf_vs_cbr_vs_qp_energy_quality.svg
    :alt: Effect of mode on energy at constant quality

Conclusion
----------

On this machine and in this video, the encoder, the profile and the force have a much greater impact on the encoding energy than the mode.
The difference between ``qp`` and ``crf`` modes is imperceptible.

The ``cbr`` mode appears to be more efficient than the others for the libsvtav1 encoder.

Reproduce
---------

Version 4.2.0 of libsvtav1 does not support optimisation on ssim and the *random/access* prediction on ``cbr`` mode.
Although mendevi enables these default settings for the ``qp`` and ``crf`` modes, they need to be always disabled here to ensure a fair comparison between the different modes of libsvtav1.
In order to optimise PSNR and predict with low delay, you have to create the file ``callback.py`` with the following content:

.. code:: python

    import re

    from mendevi.cmd import CmdFFMPEG

    def libsvtav1_lowdelay_psnr(cmd: CmdFFMPEG, **kwargs) -> CmdFFMPEG:
        """Set tune=1 and pred-struct=1 to the svtav1 parameters."""
        if kwargs["encoder"] != "libsvtav1":
            return cmd
        encode = cmd.encode
        try:
            idx = encode.index("-svtav1-params") + 1
        except ValueError:
            encode.append("-svtav1-params")
            idx = len(encode)
            encode.append("")
        encode[idx] = (
            re.sub(r"tune=\d", r"tune=1", encode[idx])
            if "tune=" in encode[idx]
            else f"{encode[idx]}:tune=1"
        )
        encode[idx] = (
            re.sub(r"pred-struct=\d", r"pred-struct=1", encode[idx])
            if "pred-struct=" in encode[idx]
            else f"{encode[idx]}:pred-struct=1"
        )
        cmd.encode = encode
        return cmd

.. code:: shell

    for video in baolei_balloon.mkv park_joy.mkv; do
        mendevi prepare $video -p sd
        mendevi prepare $video -p fhd
    done

    mendevi encode -m crf -m cbr -m qp -r 5 -c libsvtav1 -c libx264 -c libx265 -e fast -e medium --callback callback.py reference*
    mendevi decode sample*

    mendevi probe reference* sample*
