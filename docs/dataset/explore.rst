.. _dataset_explore:

Public Datasets
===============

.. note::

    If you only need to explore the pre-recorded data, you can install *mendevi* directly with ``pip install mendevi``.
    **You do not need to follow the full installation guide** unless you plan to perform the measurements yourself.


How can I retrieve them?
------------------------

JSON
^^^^

The lightweight versions of the datasets, containing the mean values and a simplified context (few Mo),
can be accessed directly by clicking on the links provided on these pages.

Decompress with ``xz -d *.json.xz`` and load with ``json.load()`` or ``pd.read_json()``.

SQL
^^^

The exhaustive databases (several Go) containing all repetitions and per-interval powers are distributed via the torrent protocol.

If you have installed transmission-daemon :ref:`install_transmission`, everything is automated and will be stored in the ``~/.cache/mendevi`` folder. That's it!

.. note::

    Otherwise open the torrent file with the software you want to download the database, then decompress the file with ``xz -dv *.xz``.


How can I plot the data?
------------------------

A dedicated API is available for this purpose. It allows you to generate the Python code required to produce a Matplotlib figure or animation.
There are examples of commands before each figure in this documentation.

To see all available options, type

.. code:: shell

    mendevi plot --help

.. dropdown:: Display details

    .. code-block:: console

        Usage: mendevi plot [OPTIONS] DATABASE

          Draw a chart from a database.

          Parameters
          ----------
          database : pathlike, optional
              The path to the database where all measurements are stored.
              If a folder is provided, the database is created inside this folder.
          x, y : tuple[str]
              The name of the x and y axes on each window. Possible values are:
                  * act_duration: Video processing activity duration in seconds.
                  * act_duration_per_frame: Average video processing activity duration per frame in seconds.
                  * actdur: Video processing activity duration in seconds.
                  * bitrate: Video bitrate in $bit.s^{-1}$.
                  * category: 3GPP TR 26.955, 5G Video Codec Characteristics.
                  * codec: Codec name.
                  * color_primaries: The tristimulus primaries colors name.
                  * color_transfer: The non-linear transfer function name.
                  * comp_ssim: Complementary of Structural Similarity (1-SSIM).
                  * cores: Average cumulative utilisation rate of logical cores.
                  * cpu_cores: Average cumulative utilisation rate of logical cores.
                  * dec_cmd: The ffmpeg command used for decoding.
                  * dec_ram: Is the decoded video stored in RAM?.
                  * dec_scenario: Unique string specific to the decoding scenario.
                  * decode_cmd: The ffmpeg command used for decoding.
                  * decode_ram: Is the decoded video stored in RAM?.
                  * decode_scenario: Unique string specific to the decoding scenario.
                  * decoder: Name of the decoder.
                  * decoder_family: The type of decoder.
                  * decoder_type: The type of decoder.
                  * effort: Effort provided as a parameter to the encoder.
                  * enc_cmd: The ffmpeg command used for encoding.
                  * enc_ram: Is the encoded video stored in RAM?.
                  * enc_scenario: Unique string specific to the encoding scenario.
                  * encode_cmd: The ffmpeg command used for encoding.
                  * encode_ram: Is the encoded video stored in RAM?.
                  * encode_scenario: Unique string specific to the encoding scenario.
                  * encoder: Name of the encoder.
                  * encoder_family: The type of encoder.
                  * encoder_type: The type of encoder.
                  * energy: Total energy consumption in Joules.
                  * energy_per_frame: Average energy consumption per frame in Joules.
                  * eotf: The non-linear transfer function name.
                  * frames: The metadata of each frame.
                  * gamut: The tristimulus primaries colors name.
                  * gpu_cores: Average cumulative utilisation rate of GPU cores.
                  * height: Height of images in pixels.
                  * hostname: The machine name.
                  * lpips: Learned Perceptual Image Patch Similarity (LPIPS).
                  * lpips_alex: Learned Perceptual Image Patch Similarity (LPIPS) with alex.
                  * lpips_vgg: Learned Perceptual Image Patch Similarity (LPIPS) with vgg.
                  * mode: Bitrate mode, crf, cbr or qp.
                  * name: Full video basename.
                  * nb_frames: The real number of frames of the video file.
                  * nbr_frames: The real number of frames of the video file.
                  * power: Average power consumption in Watts.
                  * powers: The interval duration and the average power in each intervals.
                  * preset: Effort provided as a parameter to the encoder.
                  * prim: The tristimulus primaries colors name.
                  * primaries: The tristimulus primaries colors name.
                  * profile: Profile of the video.
                  * psnr: Peak Signal to Noise Ratio (PSNR).
                  * quality: Quality level passed to the encoder.
                  * range: Video encoding color range, 'tv' or 'pc'.
                  * rate: Video bitrate in $bit.s^{-1}$.
                  * ref_stem: Input video compact stem.
                  * ref_vid_stem: Input video compact stem.
                  * ref_video_stem: Input video compact stem.
                  * reference_stem: Input video compact stem.
                  * reference_vid_stem: Input video compact stem.
                  * reference_video_stem: Input video compact stem.
                  * rev_ssim: Complementary of Structural Similarity (1-SSIM).
                  * rms_sobel: Spatial root mean square sobel gradient complexity.
                  * rms_time_diff: Temporal root means square time difference complexity.
                  * shape: The image shapes height x width in pixels.
                  * size: The total video file size in bytes.
                  * size_per_frame: Average bitrate in byte per frame.
                  * spatial_dct: Spatial DCT complexity.
                  * ssim: Structural Similarity (SSIM).
                  * ssim_comp: Complementary of Structural Similarity (1-SSIM).
                  * ssim_rev: Complementary of Structural Similarity (1-SSIM).
                  * temp: Average temperature in C.
                  * temperature: Average temperature in C.
                  * temporal_dct: Temporal DCT complexity.
                  * threads: Number of threads provided as a parameter to the encoder.
                  * trans: The non-linear transfer function name.
                  * transfer: The non-linear transfer function name.
                  * vid_duration: Video duration in seconds.
                  * vid_hash: The hexadecimal md5 video file checksum.
                  * vid_md5: The hexadecimal md5 video file checksum.
                  * vid_name: Full video basename.
                  * vid_size: The total video file size in bytes.
                  * video_duration: Video duration in seconds.
                  * video_hash: The hexadecimal md5 video file checksum.
                  * video_md5: The hexadecimal md5 video file checksum.
                  * video_name: Full video basename.
                  * video_size: The total video file size in bytes.
                  * vif: Video Visual Information Fidelity (VIF).
                  * vmaf: Video Multi-Method Assessment Fusion (VMAF).
                  * width: Width of images in pixels.
                  * log_act_duration: Log 10 of video processing activity duration in seconds.
                  * log_act_duration_per_frame: Log 10 of average video processing activity duration per frame in seconds.
                  * log_actdur: Log 10 of video processing activity duration in seconds.
                  * log_bitrate: Log 10 of video bitrate in $bit.s^{-1}$.
                  * log_category: Log 10 of 3gpp tr 26.955, 5g video codec characteristics.
                  * log_codec: Log 10 of codec name.
                  * log_color_primaries: Log 10 of the tristimulus primaries colors name.
                  * log_color_transfer: Log 10 of the non-linear transfer function name.
                  * log_comp_ssim: Log 10 of complementary of structural similarity (1-ssim).
                  * log_cores: Log 10 of average cumulative utilisation rate of logical cores.
                  * log_cpu_cores: Log 10 of average cumulative utilisation rate of logical cores.
                  * log_dec_cmd: Log 10 of the ffmpeg command used for decoding.
                  * log_dec_ram: Log 10 of is the decoded video stored in ram?.
                  * log_dec_scenario: Log 10 of unique string specific to the decoding scenario.
                  * log_decode_cmd: Log 10 of the ffmpeg command used for decoding.
                  * log_decode_ram: Log 10 of is the decoded video stored in ram?.
                  * log_decode_scenario: Log 10 of unique string specific to the decoding scenario.
                  * log_decoder: Log 10 of name of the decoder.
                  * log_decoder_family: Log 10 of the type of decoder.
                  * log_decoder_type: Log 10 of the type of decoder.
                  * log_effort: Log 10 of effort provided as a parameter to the encoder.
                  * log_enc_cmd: Log 10 of the ffmpeg command used for encoding.
                  * log_enc_ram: Log 10 of is the encoded video stored in ram?.
                  * log_enc_scenario: Log 10 of unique string specific to the encoding scenario.
                  * log_encode_cmd: Log 10 of the ffmpeg command used for encoding.
                  * log_encode_ram: Log 10 of is the encoded video stored in ram?.
                  * log_encode_scenario: Log 10 of unique string specific to the encoding scenario.
                  * log_encoder: Log 10 of name of the encoder.
                  * log_encoder_family: Log 10 of the type of encoder.
                  * log_encoder_type: Log 10 of the type of encoder.
                  * log_energy: Log 10 of total energy consumption in joules.
                  * log_energy_per_frame: Log 10 of average energy consumption per frame in joules.
                  * log_eotf: Log 10 of the non-linear transfer function name.
                  * log_frames: Log 10 of the metadata of each frame.
                  * log_gamut: Log 10 of the tristimulus primaries colors name.
                  * log_gpu_cores: Log 10 of average cumulative utilisation rate of gpu cores.
                  * log_height: Log 10 of height of images in pixels.
                  * log_hostname: Log 10 of the machine name.
                  * log_lpips: Log 10 of learned perceptual image patch similarity (lpips).
                  * log_lpips_alex: Log 10 of learned perceptual image patch similarity (lpips) with alex.
                  * log_lpips_vgg: Log 10 of learned perceptual image patch similarity (lpips) with vgg.
                  * log_mode: Log 10 of bitrate mode, crf, cbr or qp.
                  * log_name: Log 10 of full video basename.
                  * log_nb_frames: Log 10 of the real number of frames of the video file.
                  * log_nbr_frames: Log 10 of the real number of frames of the video file.
                  * log_power: Log 10 of average power consumption in watts.
                  * log_powers: Log 10 of the interval duration and the average power in each intervals.
                  * log_preset: Log 10 of effort provided as a parameter to the encoder.
                  * log_prim: Log 10 of the tristimulus primaries colors name.
                  * log_primaries: Log 10 of the tristimulus primaries colors name.
                  * log_profile: Log 10 of profile of the video.
                  * log_psnr: Log 10 of peak signal to noise ratio (psnr).
                  * log_quality: Log 10 of quality level passed to the encoder.
                  * log_range: Log 10 of video encoding color range, 'tv' or 'pc'.
                  * log_rate: Log 10 of video bitrate in $bit.s^{-1}$.
                  * log_ref_stem: Log 10 of input video compact stem.
                  * log_ref_vid_stem: Log 10 of input video compact stem.
                  * log_ref_video_stem: Log 10 of input video compact stem.
                  * log_reference_stem: Log 10 of input video compact stem.
                  * log_reference_vid_stem: Log 10 of input video compact stem.
                  * log_reference_video_stem: Log 10 of input video compact stem.
                  * log_rev_ssim: Log 10 of complementary of structural similarity (1-ssim).
                  * log_rms_sobel: Log 10 of spatial root mean square sobel gradient complexity.
                  * log_rms_time_diff: Log 10 of temporal root means square time difference complexity.
                  * log_shape: Log 10 of the image shapes height x width in pixels.
                  * log_size: Log 10 of the total video file size in bytes.
                  * log_size_per_frame: Log 10 of average bitrate in byte per frame.
                  * log_spatial_dct: Log 10 of spatial dct complexity.
                  * log_ssim: Log 10 of structural similarity (ssim).
                  * log_ssim_comp: Log 10 of complementary of structural similarity (1-ssim).
                  * log_ssim_rev: Log 10 of complementary of structural similarity (1-ssim).
                  * log_temp: Log 10 of average temperature in c.
                  * log_temperature: Log 10 of average temperature in c.
                  * log_temporal_dct: Log 10 of temporal dct complexity.
                  * log_threads: Log 10 of number of threads provided as a parameter to the encoder.
                  * log_trans: Log 10 of the non-linear transfer function name.
                  * log_transfer: Log 10 of the non-linear transfer function name.
                  * log_vid_duration: Log 10 of video duration in seconds.
                  * log_vid_hash: Log 10 of the hexadecimal md5 video file checksum.
                  * log_vid_md5: Log 10 of the hexadecimal md5 video file checksum.
                  * log_vid_name: Log 10 of full video basename.
                  * log_vid_size: Log 10 of the total video file size in bytes.
                  * log_video_duration: Log 10 of video duration in seconds.
                  * log_video_hash: Log 10 of the hexadecimal md5 video file checksum.
                  * log_video_md5: Log 10 of the hexadecimal md5 video file checksum.
                  * log_video_name: Log 10 of full video basename.
                  * log_video_size: Log 10 of the total video file size in bytes.
                  * log_vif: Log 10 of video visual information fidelity (vif).
                  * log_vmaf: Log 10 of video multi-method assessment fusion (vmaf).
                  * log_width: Log 10 of width of images in pixels.

          animation : str, optional
              It work like a parametric filter over the time "lamb", to generate an animation.
              "lamb" is the parameter evolving between 0 to 1.
          color, marker : str, optional
              All points with the same value for this variable will be displayed in the same color and marker.
              Conversely, this allows points that do not share this criterion to be visually separated.
              The possible values are the same as for the x and y parameters.
          error : str, optional
              Allows you to average several points within the same error bar.
              The string provided is a Python expression or variable.
              All points with the same image across this function are grouped together.
          window : str, optional
              Rather than putting everything in the same chart, this allows you to create sub-windows.
              There will be as many sub-windows as there are different values taken by this criterion.
              The possible values are the same as for the x and y parameters.
          window_x, window_y : str, optional
              Same as window, but with precision on the axis on which to develop.
          filter : str, optional
              This allows you to filter the data to select only a portion of it.
              The character string provided must be a Boolean Python expression
              that returns True to keep the data. For example: ``enc_duration > 10 and profile == "fhd"``.
          table : str, optional
              The main sql table juste after the FROM in SELECT.
          sub : tuple[tuple[str, str]], optional
              This allows to substitute text in the generated python code, before calling it to draw the plot.
              The provided parameters are pairs of regex expression 'pattern' and 'repl'.
              It is given as argument to the function ``re.sub``.

        Options:
          -x TEXT               The code for the value to be displayed on the x-axis.
          -y TEXT               The code for the value to be displayed on the y-axis.
          -a, --animation TEXT  A python filter expression parametrized on 'lamb' in
                                [0, 1].
          -c, --color TEXT      The discriminating criterion for color.
          -m, --marker TEXT     The discriminating criterion for marker.
          -w, --window TEXT     The criterion on which to separate into sub-windows.
          -wx, --window-x TEXT  The criterion on which to separate into sub-windows
                                along x axis.
          -wy, --window-y TEXT  The criterion on which to separate into sub-windows
                                along y axis.
          -e, --error TEXT      Merge criteria for the error bar.
          -f, --filter TEXT     Data selection python expression.
          -p, --print           Flag to print the source code.
          -t, --table TEXT      Form the SQL query around this table.
          -s, --sub TEXT...     Pair of regex expression 'pattern' and 'repl' to
                                substitute in generated code.
          --help                Show this message and exit.


All datasets list
-----------------

.. toctree::
    :maxdepth: 2
    :glob:

    explore/*


How to publish your own dataset?
--------------------------------

To publish a dataset, please refer to the `README.rst <https://gitlab.inria.fr/rrichard/mendevi/-/blob/main/dataset/README.rst>`_.
