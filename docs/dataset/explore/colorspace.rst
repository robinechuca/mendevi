.. _colorspace_dataset:

Colorspace Dataset
==================

Allows you to see the impact of the color space on compression.

Download
--------

.. code:: shell

    mendevi download colorspace.db.xz.torrent

* `colorspace.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/colorspace.json.xz?inline=false>`_ (0 Mo).
* `colorspace.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/colorspace.db.xz.torrent?inline=false>`_ (0 Go).

Plots
-----

1) The reference video ``park_joy`` was losslessly transcoded with different colorspaces to form the set of reference videos ``park_joy_*``.

2) Each of the ``park_joy_*`` videos was lossly encoded by varying several parameters but **without changing the colorspace**. These videos form the ``sample*`` collection.

Distortion as a function of bitrate for several colorspaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* On the left, the sample videos are directly compared (without color conversion) to their lossless reference ``park_joy_*``.

* On the right, the sample videos are transformed back using the inverse color transformation and then, compared to the same reference ``park_joy``.

.. code:: shell

    mendevi plot '<colorspace.db>' -x rate -y psnr -y ssim_comp -c eotf -m '(prim, range)' -wx 'name=="park_joy"' -f 'codec!="ffv1"'

.. image:: /_static/media/colorspace_bdr.svg
    :alt: Distortion as a function of bitrate

Lossless color transformation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The reference videos ``park_joy_*`` are transformed back using the inverse color transformation and then, compared to the same reference ``park_joy``. In view of the PSNR, the conversion can be considered lossless.

.. code:: shell

    mendevi plot '<colorspace.db>' -x rate -y psnr -c eotf -m '(prim, range)' -f 'codec=="ffv1"'

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
        axe.plot(l, cutcutcodec.Lambdify(l2v)(l), label=min(names), color=COLORS[i%len(COLORS)])

    axe.legend()
    plt.savefig("transfer.svg", format="svg")
    plt.show()

.. image:: /_static/media/transfer.svg
    :alt: The luminosity EOTF transfer functions

Reproduce
---------

.. code:: shell

    mendevi prepare park_joy.mp4 -p fhd
    for prim in bt601 bt709 bt2020
    do
        for trans in linear gamma22 gamma28 smpte170m smpte2084
        do
            mendevi prepare park_joy.mp4 -p fhd --primaries $prim --transfer $trans --range tv
            mendevi prepare park_joy.mp4 -p fhd --primaries $prim --transfer $trans --range pc
        done
    done

    mendevi encode -r 1 -c libx264 -c libsvtav1 --mode vbr reference*
    mendevi probe --ref reference_park_joy_fhd.mp4 reference* sample*
