.. _mvcd_datset:

MVCD like
=========

This database attempts to approach the `MVCD <https://github.com/cd-athena/MVCD>`_ measurements.

.. list-table:: The parameters of this database
    :header-rows: 1

    * - Name
      - Value
      - Description (link)
      - Total
    * - video
      - ``inter4k``
      - `torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/video/inter4k.torrent?inline=false>`_
      - :math:`1000`
    * - profile
      - ``4k``
      - Same as source
      - :math:`1`
    * - resolution
      - ``2160x3840``, ``1080x1920``, ``720x1280``, ``540x960``
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
      - ``fast``
      - :ref:`enc_effort`
      - :math:`1`
    * - framerate
      - ``30``, ``60``
      - On fly
      - :math:`2`
    * - mode
      - ``crf``
      - :ref:`enc_mode`
      - :math:`1`
    * - thread
      - :math:`\left\{ 8 \right\}`
      - :ref:`enc_threads`
      - :math:`1`
    * - repeat
      - :math:`5` times
      - total repetitions
      - :math:`5`
    * - **total**
      - :math:`\prod`
      - total number of points
      - :math:`640000`

Differences
-----------

.. caution::

  The following parameters differ from the original MVCD protocol. These choices are driven by the aim of mendevi, which is to provide reliable energy measurements, rather than to follow a bitrate/distortion benchmarking protocol.

In the original MVCD experiment, the following parameters were used and differ from those adopted in this study:

.. list-table:: MVCD parameters differing from those explored here
    :header-rows: 1

    * - Encoder
      - QP
      - Effort
      - Frames
    * - ``vvc``
      - 22, 27, 32, 37
      - ``faster``
      - 64, 32
    * - ``libsvtav1``
      - 22, 27, 32, 35, 37, 46, 55
      - ``13``
      - 64, 32
    * - ``libx264``
      - 22, 27, 32, 37
      - ``ultrafast``
      - 64, 32
    * - ``libx265``
      - 22, 27, 32, 37
      - ``ultrafast``
      - 64, 32


``qp`` vs ``crf``
^^^^^^^^^^^^^^^^^

QP refers to the codec’s internal quantization parameter. Although this approach is simple and computationally efficient, it does not guarantee either a constant bitrate or a consistent quality level.
To better **reflect an industrial context** and ensure **consistency with the other mendevi datasets**, we therefore chose to use a constant quality setting in this study.

.. note::

    The MVCD QP values ``22``, ``27``, ``32`` and ``37`` are following the `JVET-AP2010 <https://vcgit.hhi.fraunhofer.de/jvet/HM/-/tree/dev-multiview444>`_ and `JVET-AO2011 <https://jvet-experts.org/doc_end_user/documents/41_Teleconference/wg11/JVET-AO2019-v1.zip>`_ norm.

effort
^^^^^^

The ``fast`` hyperparameter in mendevi is very similar to the MVCD preset parameters.
Since the encoders have evolved, **the presets no longer behave exactly as they did** in the original MVCD experiment.
To ensure **consistency with the other mendevi datasets**, we therefore used ``fast`` hyperparameter instead of replicating the MVCD presets.

framerate
^^^^^^^^^

Although the MVCD script does not change the frame rate, the documentation and database indicate that two different frame rates were tested. We therefore assume this is an error in the script and measure both 30 and 60 fps here.

gop
^^^

MVCD controls the *Group Of Pictures*, whereas by default, mendevi asks the encoder to place I-frames more intelligently at scene changes. This second approach allows for a **more classical encoding context**.

.. note::

    The `JVET-AO2011 <https://jvet-experts.org/doc_end_user/documents/41_Teleconference/wg11/JVET-AO2019-v1.zip>`_ norm says *IntraPeriod to reflect the intra refresh period in the random access test cases. The intra refresh period is dependent on the frame rate of the source and the GOP size in use: a value 32 shall be used for sequences with a frame rate equal to 20fps, 32 for 24fps, 32 for 30fps, 64 for 50fps, 64 for 60fps, and 96 for 100fps.*, which is close to MVCD choice.

threads
^^^^^^^

Although MVCD does not consider the number of threads into account, it is fixed to 8 here.

ssim
^^^^

Although MVCD does not consider the metric to optimise, ssim is choosen here.

write output
^^^^^^^^^^^^

During decoding, MVCD writes a ``.yuv`` file to the hard drive, whereas mendevi simply decodes the video and throw the result without writing anything.

duration
^^^^^^^^

MVCD encodes only the first 32 or 64 frames of each video. However, our analysis of the impact of sequence length (:ref:`duration_dataset`) demonstrates that edge effects are particularly pronounced for such short sequences. Therefore, to mitigate these effects, we retain the full video sequences in our dataset.

yuv vs rgb
^^^^^^^^^^

MVCD keep the frame in there native yuv format, while mendevi converte them into rgb to match the display device format.

Reproduce
---------

If you want to replicate more closely to the original MVCD database, you can create the file ``callback.py`` with the following content:

.. code:: python

    """Adapt the autogenerated mendevi content to match the MVCD script.

    Original script: https://github.com/cd-athena/MVCD/blob/main/run_encoding.py
    """

    import re

    from mendevi.cmd import CmdFFMPEG

    def mendevi_to_mvcd(cmd: CmdFFMPEG, **kwargs) -> str:
        """Adapt the ffmpeg mendevi command to bring it closer to original MVCD."""

        def closer(choices: dict[float], ref: float) -> object:
            """Pick up the closest choice into the dictionary."""
            keys = list(choices)
            dists = [abs(k - ref) for k in choices]
            return choices[keys[dists.index(min(dists))]]

        # clip frames and GOP
        cmd.pre = [*cmd.pre, "-frames", {30: "32", 60: "64"}[int(kwargs["fps"])], "-g", "32"]

        # crf to qp, effort to preset
        match kwargs["encoder"]:
            case "vvc":
                qp_mvcd = closer({1.0/5: 22, 2.0/5: 27, 3.0/5: 32, 4.0/5: 37}, kwargs["quality"])
                cmd = re.sub(r"-qp \d+", f"-qp {qp_mvcd}", str(cmd))
                cmd = re.sub(r"-preset \w+", "-preset faster", cmd)
            case "libsvtav1":
                qp_mvcd = closer(
                    {1.0/8: 22, 2.0/8: 27, 3.0/8: 32, 4.0/8: 35, 5.0/8: 37, 6.0/8: 46, 7.0/8: 55},
                    kwargs["quality"],
                )
                cmd = re.sub(r"-crf \d+", f"-qp {qp_mvcd}", str(cmd))
                cmd = re.sub(r"-preset \d+", "-preset 13", cmd)
            case "libx264" | "libx265":
                qp_mvcd = closer({1.0/5: 22, 2.0/5: 27, 3.0/5: 32, 4.0/5: 37}, kwargs["quality"])
                cmd = re.sub(r"-crf \d+\.?\d*", f"-qp {qp_mvcd}", str(cmd))
                cmd = re.sub(r"-preset \w+", "-preset ultrafast", cmd)

        return cmd


Then in a terminal, (omit --callback to replicate the mendevi dataset), run:

.. code:: shell

    mendevi encode \
        -r5 -n4 -e fast \
        --resolution 2160x3840 --resolution 1080x1920 --resolution 720x1280 --resolution 540x960 \
        --fps 60 --fps 30 \
        -c vvc -c libsvtav1 -c libx264 -c libx265 \
        --callback callback.py \
        -d mvcd.db {1..1000}.mp4
    mendevi decode -r5 --resolution 2160x3840 --filter fps=60 -d mvcd.db '*.mp4'  # upscale=ups
    mendevi decode -r5 -d mvcd.db '*.mp4'  # upscale=dws
    mendevi probe --psnr --ssim --vmaf --rms-sobel --rms-time-diff --spatial-dct --temporal-dct -d mvcd.db '*.mp4'
