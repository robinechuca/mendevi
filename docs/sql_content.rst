.. _sql_content

.. image:: https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/docs/images/database.svg
    :alt: SQL database diagram

.. _t_env_environement

Table t_env_environement
========================

Captures the physical characteristics and configuration of a machine. This table also captures the library version of a given measurement.

env_id
------

+--------+-----------+
| env_id | `INTEGER` |
+--------+-----------+

Unique primary key, with no particular meaning.

env_ffmpeg_version
------------------

+--------------------+--------------+
| env_ffmpeg_version | `MEDIUMTEXT` |
+--------------------+--------------+

The ffmpeg banner containing compilation options and library versions.
This is human-readable text, returned by the function `get_ffmpeg_version <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_ffmpeg_version.html>`_.

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

env_hostname
------------

+--------------+------------+
| env_hostname | `TINYTEXT` |
+--------------+------------+

The username, given by `platform.node()`, from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.

.. code:: text

    PTB-5CG4414JJD

env_kernel_version
------------------

+--------------------+------------+
| env_kernel_version | `TINYTEXT` |
+--------------------+------------+

The version of the Linux kernel, given by `platform.platform()`, from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.

.. code:: text

    Linux-6.11.0-29-generic-x86_64-with-glibc2.40

