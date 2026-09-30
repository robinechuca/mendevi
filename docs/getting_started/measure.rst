.. _measure:

Perform Measures
================

The measurement process consists of four steps.

Preparation
-----------

This step allows you to prepare the ``Reference`` video from the ``Input`` video, to ensure that the rest of the process runs well.

This step specifically ensures the reference video:

* is encoded with the lossless **libx264** codec
* has **square pixels** (1:1 ratio)
* is encoded in the **correct color space** with consistent associated metadata
* is encoded at standard **resolution** and **framerate**
* is in 8-bit or 10-bit **YUV420** pixel format
* is perfectly resized without **distortion** or **aliasing**

.. image:: /_static/media/prepare.avif
    :alt: mendevi prepare video.y4m

To see all available options, type

.. code:: shell

    mendevi prepare --help

.. dropdown:: Display details

    .. code-block:: console

        Usage: mendevi prepare [OPTIONS] VIDEO

          Pre-Process the source video before performing the transcoding measurements.

          This step is required to provide the following guarantees:

          * Ensure a square pixel ratio.
          * Ensure that you have a lossless encoded video with a codec that allows for fast decoding.
          * Ensure high-quality resizing without spectral aliasing and blur.
          * Ensure the correct management of color space and associated metadata.
          * Ensure that the appearance of the video is not distorted.
          * Ensure that the pixel format is recognised.

          Parameters
          ----------
          video : pathlike
              The source video to be prepared.
          output : pathlike, optional
              The destination folder to store the reference file.
              If not provided, it is store in the same folder as the input video.
          **kwargs : dict
              Please refer to the detailed arguments below.
          profile : str, default=autodetect
              A value among ``sd``, ``hd``, ``fhd`` or ``uhd4k``.
              This represents a typical video profile, which includes a pixel format,
              and image resolution, a sampling frequency, and a color space.
              For more details, see :py:module:`mendevi.cst.profiles`.
              By default, it is automatically detected based on the number of pixels of the video.
          fps : fractions.Fraction, optional
              The default value is defined in the profile.
              The exact frame rate of the video. The video is not encoded with a variable frame rate.
          resolution : tuple[int, int], optional
              The default value is defined in the profile.
              The resolution of the output video. The interpolation is high quality,
              ensuring minimal blurring, no spectral overlap and preservation of proportions.
          pix_fmt : str, optional
              The default value is defined in the profile.
              The pixel format of the video.
          primaries : str, optional
              The default value is defined in the profile.
              The colorspace primaries name of the tristimulus.
              The possible values are those supported by *cutcutcodec.core.colorspace.cst.PRIMARIES*.
          transfer : str, optional
              The default value is defined in the profile.
              The electro-optical transfer function
              that allows you to define the light intensity curve of the pixels.
              The possible values are those supported by *cutcutcodec.core.colorspace.cst.TRC*.
          range : str, optional
              The default value is defined in the profile.
              You can specify ``tv`` for limited range or ``pc`` for full range.

        Options:
          -o, --output PATH               The destination folder.
          -p, --profile [sd|hd|fhd|uhd4k]
                                          The video profile.
          -f, --fps FRACTION              The framerate of the reference video.
          -r, --resolution RESOLUTION     The video resolution.
          --pix_fmt PIXEL                 The video pixel format.
          --primaries [aces_ap0|aces_ap1|adobe|bt2020|bt470bg|bt470m|bt709|film|jedec-p22, ebu3213|smpte170m|smpte428, smpte428_1|smpte431|smpte432|bt601|dcip3|displayp3|ntsc|pal|smpte240m|srgb]
                                          The colorspace.
          --transfer [arib-std-b67|bt709|gamma22|gamma26|gamma28|iec61966-2-1, iec61966_2_1|ipt|linear|log100, log|log316, log_sqrt|smpte2084|smpte428, smpte428_1|smpte240m|bt1886|bt2020|bt2020-10, bt2020_10bit|bt2020-12, bt2020_12bit|bt470bg|bt470m|bt601|hlg|log|log100|log316|log_sqrt|smpte170m|iec61966-2-4, iec61966_2_4|bt1361e, bt1361|srgb|smpte431]
                                          The electro-optical transfer function.
          --range [tv|pc]                 The pixel coding range.
          --help                          Show this message and exit.

Encode
------

This phase consists of transcoding the reference video in many different ways and measuring the machine's activity during this encoding process.

.. image:: /_static/media/encode.avif
    :alt: mendevi encode reference*

To see all available options, type

.. code:: shell

    mendevi encode --help

.. dropdown:: Display details

    .. code-block:: console

      Usage: mendevi encode [OPTIONS] [VIDEOS]...

        Measures activity during encoding.

        Parameters
        ----------
        videos : tuple[pathlike]
            The source videos to be transcoded.
            It can be a glob expression, a directory or a file path.
        database : pathlike, optional
            The path to the database where all measurements are stored.
            If a folder is provided, the database is created inside this folder.
            By default, it is created right next to the video.
        **kwargs: dict
            Please refer to the detailed arguments below.
        repeat : int, default=2
            The number of times the experiment is repeated on this environment.
            This allows us to estimate the variance of measurements.
        effort : tuple[str], default=("medium",)
            The effort made to compress, `fast`, `medium` or `slow`.
        encoder : tuple[str], default=("libx264", "libsvtav1")
            The encoders and therefore the codecs to use.
            The available encoders are mendevi.cst.encoders.ENCODERS.
        points : int, default=16
            The number of different qualities to use.
            It is an indirect way to determine the CRF or the QP.
            The quality values are distributed evenly over ]0, 1[,
            for example, points=3 => qualities=[0.25, 0.5, 0.75].
        threads : int, default=8
            The theoretical number of threads used by the encoder.
            This roughly reflects the number of logical cores used.
        fps : fractions.Fraction, optional
            If provided, the reference video will be resampled on fly just before being encoded.
            This is therefore the frame rate of the transcoded video.
            If this argument is not provided, the frame rate remains unchanged.
        resolution : tuple[int, int], optional
            If provided, the reference video will be reshaped on fly just before being encoded.
            This is therefore the resolution of the transcoded video.
            If this argument is not provided, the resolution remains unchanged.
        pix_fmt : str, optional
            If provided, A pixel conversion is performed during encoding.
        mode : tuple[str], default = ("crf",)
            Text that is ``crf`` if the quality is constant,
            ``cbr`` if the bitrate is constant,
            or ``qp`` for the internal quantification constant.
        filter : str, optional
            A video ffmpeg filter (after -vf) which applies at the time of transcoding,
            more precisely between decoding and conversion. It is a kind of pre-conversion.
        callback : str, optional
            The name of the custom function to change the cmd, the signature must match:
            def any(cmd: CmdFFMPEG, **kwargs) -> list[str] | str | CmdFFMPEG:
                ...
        ram : float
            The threshold for deciding where to copy videos. Copy in /dev/shm if
            ``available_ram_memory > ram * video_size``, otherwise, copy to the /tmp folder.

      Options:
        -d, --database PATH             The database path.
        -r, --repeat INTEGER            The number of times the encoding is repeated
                                        on this machine.
        -e, --effort [fast|medium|slow]
                                        The compression effort (default = medium).
        -c, --encoder [av1_nvenc|av1_vaapi|h264_nvenc|h264_vaapi|hevc_nvenc|hevc_vaapi|libaom-av1|libopenh264|librav1e|libsvtav1|libvpx-vp9|libx264|libx265|vp9_vaapi|vvc]
                                        The encoder name.
        -n, --points INTEGER            The number of quality point per encoder.
        -t, --threads INTEGER           The number of threads used by encoders.
        -f, --fps FRACTION              The optional framerate conversion during
                                        encoding.
        --resolution RESOLUTION         The optional video shape conversion during
                                        encoding.
        --pix_fmt PIXEL                 The optional pixel format conversion during
                                        encoding.
        -m, --mode [crf|cbr|qp]         The optional bitrate mode (crf, cbr or qp)
                                        (default = crf).
        --filter TEXT                   The ffmpeg filter to apply before encoding.
        --callback CALLBACK             User defined function to adapt the cmd.
        --ram RAM                       'yes', 'no' or threshold: To manage video
                                        copy in ramdisk or local disk.
        --help                          Show this message and exit.

Probe
-----

This phase calculates the various metrics and properties of a transcoded video.

.. image:: /_static/media/probe.avif
    :alt: mendevi probe reference* sample*

To see all available options, type

.. code:: shell

    mendevi probe --help

.. dropdown:: Display details

    .. code-block:: console

        Usage: mendevi probe [OPTIONS] [VIDEOS]...

          Measure the video properties and metrics.

          Parameters
          ----------
          videos : tuple[pathlike], optional
              All videos to be analysed. It can be a glob expression, a directory or a file path.
          database : pathlike, optional
              The path to the database where all measurements are stored.
              If a folder is provided, the database is created inside this folder.
          **kwargs: dict
              Please refer to the detailed arguments below.
          ref : tuple(pathlike), optional
              If provided, in addition to the original video ``o``,
              which has been transcoded to produce video ``x``,
              the metrics will also be calculated in relation to these reference videos ``ref``.
              Finaly comparatives metrics will be between ``o`` and ``x``, and also ``ref`` and ``x``.
          lpips_alex, lpips_vgg, psnr, ssim, vif, vmaf : boolean
              If True, compute the comparative video metric, otherwise, skip it.
          rms_sobel, rms_time_diff, spatial_dct, temporal_dct, uvq : boolean
              If True, compute the absolute uvq metric, otherwise, skip it.

        Options:
          -d, --database PATH             The database path.
          -r, --ref PATH                  The reference video for comparative metrics.
          --lpips-alex / --no-lpips-alex  Compute the LPIPS-ALEX or not.
          --lpips-vgg / --no-lpips-vgg    Compute the LPIPS-VGG or not.
          --psnr / --no-psnr              Compute the PSNR or not.
          --rms-sobel / --no-rms-sobel    Compute the C_sob or not.
          --rms-time-diff / --no-rms-time-diff
                                          Compute the C_td or not.
          --spatial-dct / --no-spatial-dct
                                          Compute the C_dct or not.
          --ssim / --no-ssim              Compute the SSIM or not.
          --temporal-dct / --no-temporal-dct
                                          Compute the H_dct or not.
          --uvq / --no-uvq                Compute the UVQ or not.
          --vif / --no-vif                Compute the VIF or not.
          --vmaf / --no-vmaf              Compute the VMAF or not.
          --help                          Show this message and exit.

Decode
------

This phase consists of measuring the machine's activity during video decoding.

.. image:: /_static/media/decode.avif
    :alt: mendevi decode reference* sample*

To see all available options, type

.. code:: shell

    mendevi decode --help

.. dropdown:: Display details

    .. code-block:: console

        Usage: mendevi decode [OPTIONS] [VIDEOS]...

          Measures activity during decoding.

          Parameters
          ----------
          videos : tuple[pathlike], optional
              All videos to be decoded. It can be a glob expression, a directory or a file path.
          database : pathlike, optional
              The path to the database where all measurements are stored.
              If a folder is provided, the database is created inside this folder.
          **kwargs: dict
              Please refer to the detailed arguments below.
          repeat : int, default=5
              The number of times the experiment is repeated on this environment.
              This allows us to estimate the variance of measurements.
          resolution : tuple[int, int], optional
              If provided, the decoded video will be reshaped on fly.
              If this argument is not provided, the resolution remains unchanged.
          filter : str, optional
              The additional ffmpeg video filter (after the -vf command)
              to be applied immediately after decoding and before other conversions.
          family : tuple[str], default=("cpu",)
              The nature of the decoder.
              "cpu" is always working, and "cuvid" requires compatible nvidia gpu.
          callback : str, optional
              The name of the custom function to change the cmd, the signature must match:
              def any(cmd: CmdFFMPEG, **kwargs) -> list[str] | str | CmdFFMPEG:
                  ...
          ram : float
              The threshold for deciding where to copy videos. Copy in /dev/shm if
              ``available_ram_memory > ram * video_size``, otherwise, copy to the /tmp folder.

        Options:
          -d, --database PATH         The database path.
          -r, --repeat INTEGER        The number of times the decoding is repeated on
                                      this machine.
          --resolution RESOLUTION     The optional video shape conversion during
                                      decoding.
          --filter TEXT               The ffmpeg filter to apply on fly.
          --family [cpu|vaapi|cuvid]  The family of decoders.
          --callback CALLBACK         User defined function to adapt the cmd.
          --ram RAM                   'yes', 'no' or threshold: To manage video copy
                                      in ramdisk or local disk.
          --help                      Show this message and exit.
