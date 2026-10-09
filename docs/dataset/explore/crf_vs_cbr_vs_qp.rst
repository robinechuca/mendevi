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
      - ``libsvtav1``, ``libx264``
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
      - :math:`2` times
      - total repetitions
      - :math:`2`
    * - video
      - ``park_joy``
      - `ctc <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/video/ctc.torrent?inline=false>`_
      - :math:`1`
    * - **total**
      - :math:`\prod`
      - total number of points
      - :math:`768`

Download
--------

.. code:: shell

    mendevi download crf_vs_cbr_vs_qp.db.xz.torrent

* `crf_vs_cbr_vs_qp.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/crf_vs_cbr_vs_qp.json.xz?inline=false>`_ (754 Ko).
* `crf_vs_cbr_vs_qp.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/crf_vs_cbr_vs_qp.db.xz.torrent?inline=false>`_ (345 Mo).

Plots
-----

Effect of mode on energy
^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot crf_vs_cbr_vs_qp.db -x bitrate -y energy -wx profile -wy encoder -c mode -m effort

.. image:: /_static/media/crf_vs_cbr_vs_qp_energy.svg
    :alt: Effect of mode on energy

Reproduce
---------

Version 4.2.0 of libsvtav1 does not support optimisation on ssim or the *random/access* prediction.
Although mendevi enables these default settings for the ``qp`` and ``crf`` modes, they need to be disabled here to ensure a fair comparison.
In order to optimise PSNR and predict with low delay, you have to create the file ``callback.py`` with the following content:

.. code:: python

    import re

    from mendevi.cmd import CmdFFMPEG

    def libsvtav1_lowdelay_psnr(cmd: CmdFFMPEG, **kwargs) -> CmdFFMPEG:
        """Add tune=1 and pred-struct=1 to the svtav1 parameters."""
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

    mendevi prepare park_joy.mkv -p sd
    mendevi prepare park_joy.mkv -p fhd

    mendevi encode -m crf -m cbr -m qp -c libx264 -c libsvtav1 -e fast -e medium --callback callback.py reference*
    mendevi decode sample*

    mendevi probe reference* sample*
