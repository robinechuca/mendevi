.. _measure:

Perform Measures
================

The measurement process consists of four steps.

Preparation
-----------

This step allows you to prepare the ``Reference`` video from the ``Input`` video, to ensure that the rest of the process runs well.

This step specifically ensures the reference video:

* is encoded with the lossless **ffv1** codec
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


:::{dropdown} Display details
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
:::



Encode
------

This phase consists of transcoding the reference video in many different ways and measuring the machine's activity during this encoding process.

.. image:: /_static/media/encode.avif
    :alt: mendevi encode reference*

To see all available options, type

.. code:: shell

    mendevi encode --help

Probe
-----

This phase calculates the various metrics and properties of a transcoded video.

.. image:: /_static/media/probe.avif
    :alt: mendevi probe reference* sample*

To see all available options, type

.. code:: shell

    mendevi probe --help

Decode
------

This phase consists of measuring the machine's activity during video decoding.

.. image:: /_static/media/decode.avif
    :alt: mendevi decode reference* sample*

To see all available options, type

.. code:: shell

    mendevi decode --help
