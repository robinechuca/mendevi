.. _sql_content:

SQL Database Content
====================

.. image:: /_static/media/sql_database.svg
    :alt: SQL database diagram

For a more detailed analysis of constraints and relationships, see the contents of the function
:py:func:`mendevi.database.create.create_database`.


.. _t_act_activity:

Table t_act_activity
--------------------

+----------------------------+-------------+-------------------------------+
| :ref:`act_id`              | *INTEGER*   | key                           |
+----------------------------+-------------+-------------------------------+
| :ref:`act_start`           | *TIMESTAMP* | date when measures start      |
+----------------------------+-------------+-------------------------------+
| :ref:`act_duration`        | *FLOAT*     | duration of measures          |
+----------------------------+-------------+-------------------------------+
| :ref:`act_rapl_dt`         | *LONGBLOB*  | RAPL measures intervals       |
+----------------------------+-------------+-------------------------------+
| :ref:`act_rapl_power`      | *LONGBLOB*  | RAPL power values             |
+----------------------------+-------------+-------------------------------+
| :ref:`act_wattmeter_dt`    | *LONGBLOB*  | wattmeter measures intervals  |
+----------------------------+-------------+-------------------------------+
| :ref:`act_wattmeter_power` | *LONGBLOB*  | wattmeter power values        |
+----------------------------+-------------+-------------------------------+
| :ref:`act_gpu_dt`          | *LONGBLOB*  | GPU measures intervals        |
+----------------------------+-------------+-------------------------------+
| :ref:`act_gpu_core`        | *LONGBLOB*  | GPU usage values              |
+----------------------------+-------------+-------------------------------+
| :ref:`act_gpu_memory`      | *LONGBLOB*  | GPU memory usage              |
+----------------------------+-------------+-------------------------------+
| :ref:`act_gpu_power`       | *LONGBLOB*  | GPU power values              |
+----------------------------+-------------+-------------------------------+
| :ref:`act_ps_dt`           | *LONGBLOB*  | time intervals for ps         |
+----------------------------+-------------+-------------------------------+
| :ref:`act_ps_core`         | *LONGBLOB*  | core usage values             |
+----------------------------+-------------+-------------------------------+
| :ref:`act_ps_temp`         | *JSON*      | temperature of all devices    |
+----------------------------+-------------+-------------------------------+
| :ref:`act_ps_ram`          | *LONGBLOB*  | RAM usage values              |
+----------------------------+-------------+-------------------------------+

Captures machine activity over a period of time.

.. _act_id:

act_id
^^^^^^

Unique primary key, with no particular meaning.

.. _act_start:

act_start
^^^^^^^^^

The date when the measure starts, the number of second from the 1st january 1970 at 00:00:00 UTC.

.. _act_duration:

act_duration
^^^^^^^^^^^^

The duration of the measurement in seconds.

.. _act_rapl_dt:

act_rapl_dt
^^^^^^^^^^^

The list of each rapl measures duration in seconds.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. _act_rapl_power:

act_rapl_power
^^^^^^^^^^^^^^

List of average power measurement in w with the wattmeter directly integrated into the processor *power/energy-pkg/*.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. important::

    The **perf** library must be installed.
    Refer the :ref:`install_perf` guide.

.. note::

    To access all information, the programme may require root privileges.
    Or you must give the permission with ``sudo sysctl -w kernel.perf_event_paranoid=0``,
    otherwise, the sensor is not reachable.
    To make it permanent, create the file ``/etc/sysctl.d/99-perf.conf`` with the content ``kernel.perf_event_paranoid = 0``.

.. _act_wattmeter_dt:

act_wattmeter_dt
^^^^^^^^^^^^^^^^

The list of time intervals in seconds between two consecutive wattmeter measures.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. tip::

    Only available for the measures taken on grid'5000.

.. _act_wattmeter_power:

act_wattmeter_power
^^^^^^^^^^^^^^^^^^^

The sampled external wattmeter measurement in w.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. tip::

    Only available for the measures taken on grid'5000.

.. _act_gpu_dt:

act_gpu_dt
^^^^^^^^^^

The list of time intervals in seconds between two consecutive GPU measures.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. tip::

    Only available for the measures taken with NVIDIA GPU.

.. _act_gpu_core:

act_gpu_core
^^^^^^^^^^^^

The list of time intervals in seconds between two consecutive GPU measures.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_tensor`.

.. tip::

    Only available for the measures taken with NVIDIA GPU.

.. _act_gpu_memory:

act_gpu_memory
^^^^^^^^^^^^^^

The list of time intervals in seconds between two consecutive GPU measures.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_tensor`.

.. tip::

    Only available for the measures taken with NVIDIA GPU.

.. _act_gpu_power:

act_gpu_power
^^^^^^^^^^^^^

The tensor of the sampled powers for each GPU.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_tensor`.

.. tip::

    Only available for the measures taken with NVIDIA GPU.

.. _act_ps_dt:

act_ps_dt
^^^^^^^^^

The list of the duration of each measurement point (in second).
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. _act_ps_core:

act_ps_core
^^^^^^^^^^^

The percent usage of each logical core average activity for each interval.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_tensor`.

.. _act_ps_temp:

act_ps_temp
^^^^^^^^^^^

The temperatures measured at each moment for all sensors. The data is presented in the form of a JSON dictionary that associates each sensor name with the list of temperatures recorded at each time interval :ref:`act_ps_dt`.

.. _act_ps_ram:

act_ps_ram
^^^^^^^^^^

The sampled total usage of ram in bytes.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.


.. _t_vid_video:

Table t_vid_video
-----------------

+--------------------------+----------------+---------------------------------+
| :ref:`vid_id`            | *BINARY(128)*  | the video key                   |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_name`          | *TEXT*         | the basename of the video file  |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_codec`         | *TINYTEXT*     | the small codec name            |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_duration`      | *FLOAT*        | the video duration              |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_eotf`          | *TINYTEXT*     | the color transfer name         |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_fps`           | *FLOAT*        | the framerate                   |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_frames`        | *JSON*         | detailed content of all frames  |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_gamut`         | *TINYTEXT*     | the color primaries name        |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_height`        | *SMALLINT*     | video height in pixels          |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_pix_fmt`       | *TINYTEXT*     | bit depth and subsampling name  |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_range`         | *TINYTEXT*     | full range (pc) or limited (tv) |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_size`          | *BIGINT*       | file size in bytes              |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_width`         | *SMALLINT*     | video width in pixels           |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_rms_sobel`     | *LONGLONGBLOB* | spatial sobel rms metric values |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_rms_time_diff` | *LONGLONGBLOB* | temporal rms metric values      |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_spatial_dct`   | *LONGLONGBLOB* | spatial dct metric values       |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_temporal_dct`  | *LONGLONGBLOB* | temporal dct metric values      |
+--------------------------+----------------+---------------------------------+
| :ref:`vid_uvq`           | *LONGLONGBLOB* | UVQ metric values               |
+--------------------------+----------------+---------------------------------+

Contains the essential absolute characteristics of a video file.

.. _vid_id:

vid_id
^^^^^^

The md5 128 bits checksum of the video file. The names of transcoded videos include this signature encoded in base32.

.. _vid_name:

vid_name
^^^^^^^^

The base name of the video file, including the suffix:

.. code:: text

    sample_74d47vez2trcs3uupnjzclz4mm.mp4

.. _vid_codec:

vid_codec
^^^^^^^^^

The name of the video codec, caught by ``cutcutcodec.get_codec_video()``:

.. code:: text

    av1

.. _vid_duration:

vid_duration
^^^^^^^^^^^^

The accurate video duration in second, including the display time of the last frame.
Catched by ``cutcutcodec.get_duration_video()``.

.. _vid_eotf:

vid_eotf
^^^^^^^^

The name of the Electro Optical Transfer Function present in the metadata, or the most probable one if not.
Catched by ``cutcutcodec.get_colorspace().transfer``.

.. code:: text

    bt1361e, bt1361

.. _vid_fps:

vid_fps
^^^^^^^

The theorical framerate in Hz written in the file metadata.
Catched by ``cutcutcodec.get_rate_video()``. Very often, the exact value is a fraction with a denominator limited to 1001.

.. _vid_frames:

vid_frames
^^^^^^^^^^

The list containing all the metadata for each frame.

.. code:: yaml

    [
        {
            "best_effort_timestamp": "0",
            "best_effort_timestamp_time": "0.000000",
            "chroma_location": "unspecified",
            "color_primaries": "smpte170m",
            "color_range": "tv",
            "color_space": "smpte170m",
            "color_transfer": "bt709",
            "crop_bottom": "0",
            "crop_left": "0",
            "crop_right": "0",
            "crop_top": "0",
            "duration": "1001",
            "duration_time": "0.041708",
            "height": "480",
            "interlaced_frame": "0",
            "key_frame": "1",
            "lossless": "0",
            "media_type": "video",
            "pict_type": "I",
            "pix_fmt": "yuv420p",
            "pkt_dts": "0",
            "pkt_dts_time": "0.000000",
            "pkt_pos": "48",
            "pkt_size": "147504",
            "pts": "0",
            "pts_time": "0.000000",
            "repeat_pict": "0",
            "sample_aspect_ratio": "1:1",
            "stream_index": "0",
            "top_field_first": "0",
            "width": "720"
        },
        ...
    ]

.. _vid_gamut:

vid_gamut
^^^^^^^^^

The name of the colorspace primaries present in the metadata, or the most probable one if not.
Catched by ``cutcutcodec.get_colorspace().primaries``.

.. code:: text

    ntsc

.. _vid_height:

vid_height
^^^^^^^^^^

The height of the video in pixels, after being decoded.

.. _vid_pix_fmt:

vid_pix_fmt
^^^^^^^^^^^

The canonical name of the pixel format, carrying information about the color space used (yuv or rgb), subsampling (444, 420 or 422) and bit depth (8, 10 or 12).
Catched by ``cutcutcodec.get_pix_fmt()``.

.. code:: text

    yuv420p

.. _vid_range:

vid_range
^^^^^^^^^

The encoded range as a string, ``pc`` for the full range, or ``tv`` for the limited range.

.. _vid_size:

vid_size
^^^^^^^^

The total size in bytes of the video file as it appears on the disc.

.. _vid_width:

vid_width
^^^^^^^^^

The width of the video in pixels, after being decoded.

.. _vid_rms_sobel:

vid_rms_sobel
^^^^^^^^^^^^^

The serialised list of the spatial root means square sobel complexity.
Catched by ``cutcutcodec.video_metrics(video, rms_sobel=True)["rms_sobel"]``.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. _vid_rms_time_diff:

vid_rms_time_diff
^^^^^^^^^^^^^^^^^

The serialised list of the temporal root means square time difference.
Catched by ``cutcutcodec.video_metrics(video, rms_time_diff=True)["rms_time_diff"]``.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. _vid_spatial_dct:

vid_spatial_dct
^^^^^^^^^^^^^^^

The serialised list of the spatial dct based complexity.
Catched by ``cutcutcodec.video_metrics(video, spatial_dct=True)["spatial_dct"]``.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. _vid_temporal_dct:

vid_temporal_dct
^^^^^^^^^^^^^^^

The serialised list of the temporal dct based complexity.
Catched by ``cutcutcodec.video_metrics(video, temporal_dct=True)["temporal_dct"]``.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. _vid_uvq:

vid_uvq
^^^^^^^

The serialised list of the non comparative `Google Universale Video Quality Model <https://github.com/google/uvq>`_ metric. Catched by ``cutcutcodec.video_metrics(video, uvq=True)["uvq"]``.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.


.. _t_met_metric:

Table t_met_metric
------------------

+-----------------------+---------------+---------------------------------------+
| :ref:`met_id`         | *INTEGER*     | key                                   |
+-----------------------+---------------+---------------------------------------+
| :ref:`met_ref_vid_id` | *BINARY(128)* | the reference video identifier        |
+-----------------------+---------------+---------------------------------------+
| :ref:`met_dis_vid_id` | *BINARY(128)* | the identifier of the distorted video |
+-----------------------+---------------+---------------------------------------+
| :ref:`met_lpips_alex` | *LONGBLOB*    | values of LPIPS ALEX metric           |
+-----------------------+---------------+---------------------------------------+
| :ref:`met_lpips_vgg`  | *LONGBLOB*    | values of LPIPS VGG metric            |
+-----------------------+---------------+---------------------------------------+
| :ref:`met_psnr`       | *LONGBLOB*    | values of PSNR metric                 |
+-----------------------+---------------+---------------------------------------+
| :ref:`met_ssim`       | *LONGBLOB*    | values of SSIM metric                 |
+-----------------------+---------------+---------------------------------------+
| :ref:`met_vif`        | *LONGBLOB*    | values of VIF metric                  |
+-----------------------+---------------+---------------------------------------+
| :ref:`met_vmaf`       | *LONGBLOB*    | values of VMAF metric                 |
+-----------------------+---------------+---------------------------------------+

Compare the quality of a distorted video against a reference video using comparative metrics.

.. _met_id:

met_id
^^^^^^

Unique primary key, with no particular meaning.

.. _met_ref_vid_id:

met_ref_vid_id
^^^^^^^^^^^^^^

The never-null identifier of the reference video, as defined in :ref:`vid_id`.

.. _met_dis_vid_id:

met_dis_vid_id
^^^^^^^^^^^^^^

The never-null identifier of the distorted video, as defined in :ref:`vid_id`.

.. _met_lpips_alex:

met_lpips_alex
^^^^^^^^^^^^^^

The serialised list of the LPIPS comparative metric using the ALEX neural network.
Catched by ``cutcutcodec.video_metrics(dis, ref, lpips_alex=True)["lpips_alex"]``.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. _met_lpips_vgg:

met_lpips_vgg
^^^^^^^^^^^^^^

The serialised list of the LPIPS comparative metric using the VGG neural network.
Catched by ``cutcutcodec.video_metrics(dis, ref, lpips_vgg=True)["lpips_vgg"]``.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. _met_psnr:

met_psnr
^^^^^^^^

The serialised list of the yuv (6, 1, 1) peak signal to noise ratio comparative metric.
Catched by ``cutcutcodec.video_metrics(dis, ref, psnr=True)["psnr"]``.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. _met_ssim:

met_ssim
^^^^^^^^

The serialised list of the yuv (6, 1, 1) (gauss win 11x11) structural similarity index measure comparative metric.
Catched by ``cutcutcodec.video_metrics(dis, ref, ssim=True)["ssim"]``.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. _met_vif:

met_vif
^^^^^^^

The serialised list of the visual information fidelity comparative metric on luminance.
Catched by ``cutcutcodec.video_metrics(dis, ref, vif=True)["vif"]``.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.

.. _met_vmaf:

met_vmaf
^^^^^^^^

The serialised list of the comparative metric `Netflix Video Multi-Method Assessment Fusion <https://github.com/Netflix/vmaf>`_ metric.
Catched by ``cutcutcodec.video_metrics(dis, ref, vmaf=True)["vmaf"]``.
To deserialize into an exploitable numpy array, please use the function :py:func:`mendevi.database.serialize.binary_to_list`.


.. _t_env_environment:

Table t_env_environment
-----------------------

+-------------------------------+--------------+-------------------------------+
| :ref:`env_id`                 | *INTEGER*    | Key                           |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_ffmpeg_version`     | *MEDIUMTEXT* | the full ffmpeg version       |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_hostname`           | *TINYTEXT*   | the username                  |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_kernel_version`     | *TINYTEXT*   | the linux kernel version      |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_librav1e_version`   | *MEDIUMTEXT* | the version of librav1e       |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_libsvtav1_version`  | *MEDIUMTEXT* | the version of libsvtav1      |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_libvpx_vp9_version` | *MEDIUMTEXT* | the version of libvpx-vp9     |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_libx265_version`    | *MEDIUMTEXT* | the version of libx265        |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_logical_cores`      | *INTEGER*    | the number of visible cpu     |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_lshw`               | *JSON*       | the machine config (lshw)     |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_lspci`              | *LONGTEXT*   | the machine config (lspci)    |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_physical_cores`     | *INTEGER*    | the real number of cpu        |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_pip_freeze`         | *MEDIUMTEXT* | all python packages version   |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_processor`          | *TINYTEXT*   | the processos family          |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_python_compiler`    | *TINYTEXT*   | name of python compiler       |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_python_version`     | *TINYTEXT*   | the python version            |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_ram`                | *INTEGER*    | Total amount of RAM           |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_swap`               | *INTEGER*    | Total amount of SWAP          |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_system_version`     | *MEDIUMTEXT* | the OS version                |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_vvc_version`        | *MEDIUMTEXT* | the version of vvenc          |
+-------------------------------+--------------+-------------------------------+
| :ref:`env_idle_act_id`        | *INTEGER*    | IDLE as :ref:`t_act_activity` |
+-------------------------------+--------------+-------------------------------+

Captures the physical characteristics and configuration of a machine. This table also captures the library version of a given measurement.

.. _env_id:

env_id
^^^^^^

Unique primary key, with no particular meaning.

.. _env_ffmpeg_version:

env_ffmpeg_version
^^^^^^^^^^^^^^^^^^

The ffmpeg banner containing compilation options and library versions.
This is human-readable text, returned by the function :py:func:`mendevi.measures.context.get_ffmpeg_version`.

Please follow the :ref`install_ffmpeg`` section.

.. code:: text

    ffmpeg version N-120220-g934e1c23b0 Copyright (c) 2000-2025 the FFmpeg developers
    built with gcc 14 (Ubuntu 14.2.0-4ubuntu2)
    configuration: --prefix=/home/rrichard/ffmpeg_build --pkg-config-flags=--static --extra-cflags=-I/home/rrichard/ffmpeg_build/include --extra-ldflags=-L/home/rrichard/ffmpeg_build/lib --extra-libs='-lpthread -lm' --ld=g++ --bindir=/home/rrichard/bin --enable-gpl --enable-gnutls --enable-libaom --enable-libass --enable-libfdk-aac --enable-libfreetype --enable-libmp3lame --enable-libopus --enable-libsvtav1 --enable-libdav1d --enable-libvorbis --enable-libvpx --enable-libx264 --enable-libx265 --enable-libvvenc --enable-nonfree
    libavutil      60.  4.101 / 60.  4.101
    libavcodec     62.  6.100 / 62.  6.100
    libavformat    62.  1.101 / 62.  1.101
    libavdevice    62.  0.100 / 62.  0.100
    libavfilter    11.  1.100 / 11.  1.100
    libswscale      9.  0.100 /  9.  0.100
    libswresample   6.  0.100 /  6.  0.100

.. _env_hostname:

env_hostname
^^^^^^^^^^^^

The machine name, given by ``platform.node()``, from the function :py:func:`mendevi.measures.context.get_platform`.

.. code:: text

    paradoxe-32.rennes.grid5000.fr

.. _env_kernel_version:

env_kernel_version
^^^^^^^^^^^^^^^^^^

The version of the Linux kernel, given by ``platform.platform()``, from the function :py:func:`mendevi.measures.context.get_platform`.

.. code:: text

    Linux-6.11.0-29-generic-x86_64-with-glibc2.40

.. _env_librav1e_version:

env_librav1e_version
^^^^^^^^^^^^^^^^^^^^

The version of rav1e excecutable file, whitch is a good candidate for ffmpeg librav1e encoder, from the function :py:func:`mendevi.measures.context.get_librav1e_version`.

.. code:: text

    rav1e 0.8.0 (p20250624-1-gb7bf390) (release)
    rustc 1.91.1 (ed61e7d7e 2025-11-07) x86_64-unknown-linux-gnu
    Compiled CPU Features: adx,aes,avx,avx2,bmi1,bmi2,cmpxchg16b,f16c,fma,fxsr,lzcnt,movbe,pclmulqdq,popcnt,rdrand,rdseed,sse,sse2,sse3,sse4.1,sse4.2,ssse3,xsave,xsavec,xsaveopt,xsaves
    Runtime Assembly Support: Enabled
    Runtime Assembly Level: AVX2
    Threading: Enabled
    Unstable Features: Disabled
    Compiler Flags: -C target-cpu=native

.. _env_libsvtav1_version:

env_libsvtav1_version
^^^^^^^^^^^^^^^^^^^^^

The version of the libsvtav1 encoder and the version of the compiler for this library. It comes from the function :py:func:`mendevi.measures.context.get_libsvtav1_version`.

.. code:: text

    v3.1.0-327-gf42da0a0
    GCC 14.2.0 64 bit

.. _env_libvpx_vp9_version:

env_libvpx_vp9_version
^^^^^^^^^^^^^^^^^^^^^^

The version of the libvpx-vp9 encoder. It comes from the function :py:func:`mendevi.measures.context.get_libvpx_vp9_version`.

.. code:: text

    v1.14.1

.. _env_libx265_version:

env_libx265_version
^^^^^^^^^^^^^^^^^^^

The version of the libx265 encoder and the version of the compiler for this library. It comes from the function :py:func:`mendevi.measures.context.get_libx265_version`.

.. code:: text

    4.1+188-cd4f0d6e9
    [Linux][GCC 14.2.0][64 bit] 8bit+10bit+12bit
    MMX2 SSE2Fast LZCNT SSSE3 SSE4.2 AVX FMA3 BMI2 AVX2

.. _env_logical_cores:

env_logical_cores
^^^^^^^^^^^^^^^^^

The number of logical (threaded) cores, in general more than the number of physical cores. It is given by ``psutil.cpu_count(logical=True)``, from the function :py:func:`mendevi.measures.context.get_platform`.

.. _env_lshw:

env_lshw
^^^^^^^^

A wealth of information on machine components, processor architecture, etc. Based on ``lshw -json``.

.. important::

    The **lshw** library must be installed.
    Refer the :ref:`install_lshw` guide.

.. note::

    To access all information, the programme must have root privileges.
    Otherwise, some of the information will be missing.

.. code:: yaml

    {
        "id": "ptb-5cg4414jjd",
        "class": "system",
        "claimed": true,
        "description": "Computer",
        "width": 64,
        "capabilities": {
            "smp" : "Symmetric Multi-Processing",
            "vsyscall32" : "processus 32 bits"
        },
        "children" : [
            {
                "id": "core",
                "class": "bus",
                "claimed": true,
                "description": "Motherboard",
                "physid": "0",
                "children": ...
            },
            {
                "id" : "cpu",
                "class" : "processor",
                ...
                "configuration" : {
                    "microcode" : "36"
                },
                "capabilities" : {
                    "fpu" : "mathematical co-processor",
                    ...
                    "cpufreq" : "CPU Frequency scaling"
                }
            }
        ]
    }

.. _env_lspci:

env_lspci
^^^^^^^^^

Informations on periferics, based on ``lspci -k``.

.. _env_physical_cores:

env_physical_cores
^^^^^^^^^^^^^^^^^^

The number of physical cores, in general less than the number of logical physical cores. It is given by ``psutil.cpu_count(logical=False)``, from the function :py:func:`mendevi.measures.context.get_platform`.

.. _env_pip_freeze:

env_pip_freeze
^^^^^^^^^^^^^^

The list of the version of the python packages. The function :py:func:`mendevi.measures.context.get_pip_freeze` parse the command ``uv pip freeze``.


.. code:: text

    aiohappyeyeballs==2.6.1
    aiohttp==3.11.16
    aiosignal==1.3.2
    ansible-core==2.17.11
    astroid==3.3.10
    asttokens==3.0.0
    attrs==25.3.0
    av==14.3.0
    bcrypt==4.3.0
    black==25.1.0
    cairocffi==1.7.1
    CairoSVG==2.7.1
    certifi==2025.1.31
    cffi==1.17.1
    charset-normalizer==3.4.1
    click==8.1.8
    colorama==0.4.6
    ...

.. _env_processor:

env_processor
^^^^^^^^^^^^^

The proccessor family, given by ``platform.processor()``, from the function :py:func:`mendevi.measures.context.get_platform`.

.. code:: text

    x86_64

.. _env_python_compiler:

env_python_compiler
^^^^^^^^^^^^^^^^^^^

The cython compiler and version, given by ``platform.python_compiler()``, from the function :py:func:`mendevi.measures.context.get_platform`.

.. code:: text

    GCC 14.2.0

.. _env_python_version:

env_python_version
^^^^^^^^^^^^^^^^^^

The version of python, given by ``platform.python_version()``, from the function :py:func:`mendevi.measures.context.get_platform`.

.. code:: text

    3.13.2

.. _env_ram:

env_ram
^^^^^^^

The total physical memory (exclusive swap) in bytes, given by ``psutil.virtual_memory().total``, from the function :py:func:`mendevi.measures.context.get_platform`.

.. _env_swap:

env_swap
^^^^^^^^

The total swap memory in bytes, given by ``psutil.swap_memory().total``, from the function :py:func:`mendevi.measures.context.get_platform`.

.. _env_system_version:

env_system_version
^^^^^^^^^^^^^^^^^^

The name and the version of linux, given by ``platform.version()``,from the function :py:func:`mendevi.measures.context.get_platform`.

.. code:: text

    #29-Ubuntu SMP PREEMPT_DYNAMIC Fri Jun 13 20:29:41 UTC 2025

.. _env_vvc_version:

env_vvc_version
^^^^^^^^^^^^^^^

The version of the vvenc encoder. It comes from the function :py:func:`mendevi.measures.context.get_vvc_version`.

.. code:: text

    1.13.1

.. _env_idle_act_id:

env_idle_act_id
^^^^^^^^^^^^^^^

The id in the table :ref:`t_act_activity` of the IDLE measure of the machine.


.. _t_dec_decode:

Table t_dec_decode
------------------

+--------------------+---------------+--------------------------------+
| :ref:`dec_id`      | *INTEGER*     | Key                            |
+--------------------+---------------+--------------------------------+
| :ref:`dec_vid_id`  | *BINARY(128)* | the reference video identifier |
+--------------------+---------------+--------------------------------+
| :ref:`dec_env_id`  | *INTEGER*     | the environment identifier     |
+--------------------+---------------+--------------------------------+
| :ref:`dec_act_id`  | *INTEGER*     | the activity identifier        |
+--------------------+---------------+--------------------------------+
| :ref:`dec_cmd`     | *TEXT*        | ffmpeg command used            |
+--------------------+---------------+--------------------------------+
| :ref:`dec_decoder` | *TINYTEXT*    | the decoder name               |
+--------------------+---------------+--------------------------------+
| :ref:`dec_filter`  | *TEXT*        | additional video filter        |
+--------------------+---------------+--------------------------------+
| :ref:`dec_height`  | *SMALLINT*    | decoded height                 |
+--------------------+---------------+--------------------------------+
| :ref:`dec_log`     | *LONGTEXT*    | the standard output of the cmd |
+--------------------+---------------+--------------------------------+
| :ref:`dec_pix_fmt` | *TINYTEXT*    | decoded pixel format           |
+--------------------+---------------+--------------------------------+
| :ref:`dec_width`   | *SMALLINT*    | decoded width                  |
+--------------------+---------------+--------------------------------+

Contains the informations about video decoding.

.. _dec_id:

dec_id
^^^^^^

Unique primary key, with no particular meaning.

.. _dec_vid_id:

dec_vid_id
^^^^^^^^^^

This is the reference of the source video that has been decoded. It points to the table :ref:`t_vid_video`.

.. _dec_env_id:

dec_env_id
^^^^^^^^^^

This is the reference of the context in which the decoding took place. It points to the table :ref:`t_env_environment`.

.. _dec_act_id:

dec_act_id
^^^^^^^^^^

This is a reference of measuring the machine's activity during video decoding. It points to the table :ref:`t_act_activity`.

.. _dec_cmd:

dec_cmd
^^^^^^^

The ffmpeg command used for decoding:

.. code:: shell

    ffmpeg -threads 1 -i vid.mp4 -vf format=rgb24 -f null /dev/null

.. _dec_decoder:

dec_decoder
^^^^^^^^^^^

The name of the decoder provided to ffmpeg. If nothing has been specified, this field takes the value ``null``.

.. _dec_filter:

dec_filter
^^^^^^^^^^

The additional ffmpeg video filter (after the -vf command) applied during decoding.

.. _dec_height:

dec_height
^^^^^^^^^^

In order to adapt the size of the decoded images to the size of the terminal, the frames are resized on the fly. Here is the final height of the screen.

.. _dec_log:

dec_log
^^^^^^^

The plain utf-8 text of the standard output of the decoding cmd during execution.

.. _dec_pix_fmt:

dec_pix_fmt
^^^^^^^^^^^

During decoding, the pixels are converted into another format so that they can be displayed. This is the final format.

.. code:: text

    rgb24

.. _dec_width:

dec_width
^^^^^^^^^

In order to adapt the size of the decoded images to the size of the terminal, the frames are resized on the fly. Here is the final width of the screen.


.. _t_enc_encode:

Table t_enc_encode
------------------

+-----------------------+---------------+--------------------------------+
| :ref:`enc_id`         | *INTEGER*     | Key                            |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_src_vid_id` | *BINARY(128)* | the input video                |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_dst_vid_id` | *BINARY(128)* | the ouput transcoded video     |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_env_id`     | *INTEGER*     | the environment identifier     |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_act_id`     | *INTEGER*     | the activity identifier        |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_cmd`        | *TEXT*        | ffmpeg command used            |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_effort`     | *TINYTEXT*    | the effort made by the encoder |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_encoder`    | *TINYTEXT*    | the encoder name               |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_filter`     | *TEXT*        | additional video filter        |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_fps`        | *FLOAT*       | the input framerate            |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_height`     | *SMALLINT*    | the input frames height        |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_log`        | *LONGTEXT*    | the standard output of the cmd |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_mode`       | *TINYTEXT*    | constant or variable bitrate   |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_pix_fmt`    | *TINYTEXT*    | the input pixel format         |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_quality`    | *FLOAT*       | the encoding crf or qp         |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_threads`    | *SMALLINT*    | the number of threads used     |
+-----------------------+---------------+--------------------------------+
| :ref:`enc_width`      | *SMALLINT*    | the input frames width         |
+-----------------------+---------------+--------------------------------+

Contains the informations about video encoding.

.. _enc_id:

enc_id
^^^^^^

Unique primary key, with no particular meaning.

.. _enc_src_vid_id:

enc_src_vid_id
^^^^^^^^^^^^^^

This is the reference of the input video that enters into the encoder. It points to the table :ref:`t_vid_video`.

.. _enc_dst_vid_id:

enc_dst_vid_id
^^^^^^^^^^^^^^

This is the reference of the transcoded video that exits the encoder. It points to the table :ref:`t_vid_video`.

.. _enc_env_id:

enc_env_id
^^^^^^^^^^

This is the reference of the context in which the encoding took place. It points to the table :ref:`t_env_environment`.

.. _enc_act_id:

enc_act_id
^^^^^^^^^^

This is a reference of measuring the machine's activity during video encoding. It points to the table :ref:`t_act_activity`.

.. _enc_cmd:

enc_cmd
^^^^^^^

The ffmpeg command used for encoding:

.. code:: shell

    ffmpeg -y -i ref.mp4 -c:v libsvtav1 -crf 15 -preset 6 -svtav1-params film-grain=0:lp=3 dst.mp4

.. _enc_effort:

enc_effort
^^^^^^^^^^

The effort that the encoder puts into optimizing the bit rate distortion ratio in exchange for increased computing time.
Possible values are ``fast``, ``medium`` and ``slow``.

.. _enc_encoder:

enc_encoder
^^^^^^^^^^^

The ffmpeg encoder name. Possible values are ``libx264``, ``libx265``, ``libvpx-vp9``, ``libsvtav1`` and ``vvc``.

.. _enc_filter:

enc_filter
^^^^^^^^^^

The additional ffmpeg video filter (after the -vf command) applied during decoding.

.. _enc_fps:

enc_fps
^^^^^^^

The frame rate in Hz of the video at the encoder input.

.. _enc_height:

enc_height
^^^^^^^^^^

The number of pixel of the frames along the height dimension.

.. _enc_mode:

enc_mode
^^^^^^^^

Text that is ``cbr`` if the bit rate is constant (cbr mode), or ``vbr`` if it is variable (constant quality mode).

.. _enc_log:

enc_log
^^^^^^^

The plain utf-8 text of the standard output of the encoding cmd during execution.

.. _enc_pix_fmt:

enc_pix_fmt
^^^^^^^^^^^

The pixel format used for encoding.

.. code:: text

    yuv420p

.. _enc_quality:

enc_quality
^^^^^^^^^^^

The relative quality :math:`\in [0, 1]` that the encoder aims for the final video. This number is afinally related to the ``crf`` or ``qp`` parameter. 0 corresponds to near lossless encoding, and 1 to highly lossy encoding.

.. _enc_threads:

enc_threads
^^^^^^^^^^^

The number of threads that the encoder uses simultaneously. This is related to the CPU utilisation rate.

.. _enc_width:

enc_width
^^^^^^^^^^

The number of pixel of the frames along the width dimension.
