.. _colorspace_dataset:

Colorspace Dataset
==================

Allows you to see the impact of the color space on compression.

.. list-table:: The parameters of this database
    :header-rows: 1

    * - Name
      - Value
      - Description (link)
      - Total
    * - video
      - ``park_joy``
      - `ctc <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/video/ctc.torrent?inline=false>`_
      - :math:`1`
    * - profile
      - ``fhd``
      - `video resolution <https://gitlab.inria.fr/rrichard/mendevi/-/blob/main/mendevi/cst/profiles.py>`_
      - :math:`1`
    * - primaries
      - ``bt601``, ``bt709``, ``bt2020``
      - :ref:`vid_gamut` (in profile)
      - :math:`3`
    * - transfer
      - ``linear``, ``bt1361``, ``gamma22``, ``gamma28``, ``smpte2084``
      - :ref:`vid_eotf` (in profile)
      - :math:`5`
    * - range
      - ``tv``, ``pc``
      - :ref:`vid_range` (in profile)
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
      - ``medium``
      - :ref:`enc_effort`
      - :math:`1`
    * - mode
      - ``vbr``
      - :ref:`enc_mode`
      - :math:`1`
    * - thread
      - :math:`\left\{ 8 \right\}`
      - :ref:`enc_threads`
      - :math:`1`
    * - repeat
      - :math:`2` times
      - total repetitions
      - :math:`2`
    * - host
      - ``paradoxe-32``
      - :ref:`env_hostname`
      - :math:`1`
    * - **total**
      - :math:`\prod`
      - total number of points
      - :math:`1920`

Download
--------

.. code:: shell

    mendevi download colorspace.db.xz.torrent

* `colorspace.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/colorspace.json.xz?inline=false>`_ (845 Ko).
* `colorspace.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/colorspace.db.xz.torrent?inline=false>`_ (571 Mo).

Pipeline
--------

This is the pipeline used for measurements:

.. image:: /_static/media/colorspace.svg
    :alt: Pipeline diagram

1) The input video ``park_joy.mkv`` was losslessly transcoded with different colorspaces to form the set of reference videos ``reference_park_joy_*_fhd.mp4``, including the default ``reference_park_joy_fhd.mp4``.

2) Each of the ``reference_park_joy_*`` videos was lossly encoded by varying several parameters but **without changing the colorspace**. These videos form the ``sample*`` collection.

Plots
-----

Distortion as a function of bitrate for several colorspaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* On the left column, the sample videos are directly compared (without color conversion) to their lossless reference ``reference_park_joy_*_fhd.mp4``.

* On the right column, the sample videos are transformed back using the inverse color transformation and then, compared to the same default reference ``reference_park_joy_fhd.mp4``.

.. code:: shell

    mendevi plot colorspace.db -x rate -y ssim_comp -c eotf -m '(prim, range)' -wx "ref_stem=='park_joy'" -f "not name.startswith('ref')" -t t_met_metric

.. image:: /_static/media/colorspace_bdr.svg
    :alt: Distortion as a function of bitrate

Impact of EOTF on energy consumption
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot colorspace.db -x rate -y energy -c eotf -m '(prim, range)' -wx encoder -s 'sharey="row"' 'sharey=False'

.. image:: /_static/media/colorspace_energy.svg
    :alt: Energy as a function of bitrate

Lossless color transformation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The reference videos ``park_joy_*`` are transformed back using the inverse color transformation and then, compared to the same reference ``park_joy``. In view of the PSNR, the conversion can be considered lossless.

.. code:: shell

    mendevi plot colorspace.db -x rate -y psnr -c eotf -m '(prim, range)' -f "'reference' in name"

.. image:: /_static/media/colorspace_bij.svg
    :alt: Lossless back colorspace transformation

Visualize transfer functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    import cutcutcodec
    import matplotlib.pyplot as plt
    import torch
    from mendevi.cst.plot import COLORS, FIGSIZE

    # get curves
    l2v_names: dict = {}
    for name, (l2v, _) in cutcutcodec.core.colorspace.cst.TRC.items():
        l2v_names[l2v] = l2v_names.get(l2v, [])
        l2v_names[l2v].append(name)

    # matplotlib plot chart
    fig = plt.figure(layout="constrained", figsize=FIGSIZE)
    axe = fig.subplots()
    axe.grid()
    fig.supylabel("v")
    fig.supxlabel("l")

    # plot data
    l = torch.linspace(0, 1, 1000)
    for i, (l2v, names) in enumerate(l2v_names.items()):
        axe.plot(l, cutcutcodec.Lambdify(l2v)(l), label=min(names), color=COLORS[i])

    axe.legend()
    plt.savefig("transfer.svg", format="svg")
    plt.show()

.. image:: /_static/media/transfer.svg
    :alt: The luminosity EOTF transfer functions

Reproduce
---------

.. code:: shell

    for prim in bt601 bt709 bt2020
    do
        for trans in linear bt1361 gamma22 gamma28 smpte2084
        do
            mendevi prepare park_joy.mkv -p fhd --primaries $prim --transfer $trans --range tv
            mendevi prepare park_joy.mkv -p fhd --primaries $prim --transfer $trans --range pc
        done
    done

    mendevi encode -c libx264 -c libsvtav1 reference*
    mendevi probe --ref reference_park_joy_fhd.mp4 reference* sample*
