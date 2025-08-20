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

The username, given by ``platform.node()``, from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.

.. code:: text

    PTB-5CG4414JJD

env_kernel_version
------------------

+--------------------+------------+
| env_kernel_version | `TINYTEXT` |
+--------------------+------------+

The version of the Linux kernel, given by ``platform.platform()``, from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.

.. code:: text

    Linux-6.11.0-29-generic-x86_64-with-glibc2.40

env_libsvtav1_version
---------------------

+-----------------------+------------+
| env_libsvtav1_version | MEDIUMTEXT |
+-----------------------+------------+

The version of the libsvtav1 encoder and the version of the compiler for this library. It comes from the function `get_libsvtav1_version <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_libsvtav1_version.html>`_.

.. code:: text

    v3.0.2-103-gc10214fa
    GCC 14.2.0 64 bit

env_libvpx_vp9_version
----------------------

+------------------------+------------+
| env_libvpx_vp9_version | MEDIUMTEXT |
+------------------------+------------+

The version of the libvpx-vp9 encoder. It comes from the function `get_libvpx_vp9_version <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_libvpx_vp9_version.html>`_.

.. code:: text

    v1.14.1

env_libx265_version
-------------------

+---------------------+------------+
| env_libx265_version | MEDIUMTEXT |
+---------------------+------------+

The version of the libx265 encoder and the version of the compiler for this library. It comes from the function `get_libx265_version <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_libx265_version.html>`_.

.. code:: text

    4.1+188-cd4f0d6e9
    [Linux][GCC 14.2.0][64 bit] 8bit+10bit+12bit
    MMX2 SSE2Fast LZCNT SSSE3 SSE4.2 AVX FMA3 BMI2 AVX2

env_logical_cores
-----------------

+-------------------+---------+
| env_logical_cores | INTEGER |
+-------------------+---------+

The number of logical (threaded) cores, in general more than the number of physical cores. It is given by ``psutil.cpu_count(logical=True)``, from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.


env_lshw
--------

+----------+------+
| env_lshw | JSON |
+----------+------+

A wealth of information on machine components, processor architecture, etc.

.. important::

    The **lshw** library must be installed.
    Refer the :ref:`full_installation` guide.

.. note::

    To access all information, the programme must have root privileges.
    Otherwise, some of the information will be missing.

.. code:: json

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

env_physical_cores
------------------

+--------------------+---------+
| env_physical_cores | INTEGER |
+--------------------+---------+

The number of physical cores, in general less than the number of logical physical cores. It is given by ``psutil.cpu_count(logical=False)``, from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.

env_pip_freeze
--------------

+----------------+------------+
| env_pip_freeze | MEDIUMTEXT |
+----------------+------------+

The list of the version of the python packages. The function `get_pip_freeze <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_pip_freeze.html>`_ parse the command ``pip freeze``.


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

env_processor
-------------

+---------------+-----------+
| env_processor |  TINYTEXT |
+---------------+-----------+

The proccessor familly, given by ``platform.processor()``, from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.

.. code:: text

    x86_64

env_python_compiler
-------------------

+---------------------+----------+
| env_python_compiler | TINYTEXT |
+---------------------+----------+

The cython compiler and version, given by ``platform.python_compiler()``, from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.

.. code:: text

    GCC 14.2.0


env_python_version
------------------

+--------------------+----------+
| env_python_version | TINYTEXT |
+--------------------+----------+

The version of python, given by ``platform.python_version()``, from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.

.. code:: text

    3.13.2

env_ram
-------

+---------+---------+
| env_ram | INTEGER |
+---------+---------+

The total physical memory (exclusive swap) in bytes, given by ``psutil.virtual_memory().total``, from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.

env_swap
--------

+----------+---------+
| env_swap | INTEGER |
+----------+---------+

The total swap memory in bytes, given by ``psutil.swap_memory().total``, from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.

env_system_version
------------------

+--------------------+------------+
| env_system_version | MEDIUMTEXT |
+--------------------+------------+

The name and the version of linux, given by ``platform.version()``,from the function `get_platform <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_platform.html>`_.

.. code:: text

    #29-Ubuntu SMP PREEMPT_DYNAMIC Fri Jun 13 20:29:41 UTC 2025

env_vvc_version
---------------

+-----------------+------------+
| env_vvc_version | MEDIUMTEXT |
+-----------------+------------+

The version of the vvenc encoder. It comes from the function `get_vvc_version <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_vvc_version.html>`_.

.. code:: text

    1.13.1

env_act_id
----------

+------------+---------+
| env_act_id | INTEGER |
+------------+---------+

The id in the table :ref:`t_act_activity` of the IDLE measure of the machine.


.. _t_act_activity

Table t_act_activity
====================

Captures machine activity over a period of time.

act_id
------

+--------+-----------+
| act_id | `INTEGER` |
+--------+-----------+

Unique primary key, with no particular meaning.

act_start
---------

+-----------+-----------+
| act_start | TIMESTAMP |
+-----------+-----------+

The date when the measure starts, the number of second from the 1st january 1970 at 00:00:00 UTC.

act_duration
------------

+--------------+-------+
| act_duration | FLOAT |
+--------------+-------+

The duration of the measurement in seconds.

act_rapl_dt
-----------

+-------------+----------+
| act_rapl_dt | LONGBLOB |
+-------------+----------+

The list of time intervals in seconds between two consecutive rapl measures.
To deserialize into an exploitable numpy array, please use the function `binary_to_list <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.database.serialize.binary_to_list.html>`_.

act_rapl_power
--------------

+----------------+----------+
| act_rapl_power | LONGBLOB |
+----------------+----------+

List of average power measurement in w with the wattmeter directly integrated into the processor *power/energy-pkg/*.
To deserialize into an exploitable numpy array, please use the function `binary_to_list <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.database.serialize.binary_to_list.html>`_.

.. important::

    The **perf** library must be installed.
    Refer the :ref:`full_installation` guide.

.. note::

    To access all information, the programme may require root privileges.
    Or you must give the permission with ``sudo sysctl -w kernel.perf_event_paranoid=0``,
    otherwise, the sensor is not reachable.

act_wattmeter_dt
----------------

+------------------+----------+
| act_wattmeter_dt | LONGBLOB |
+------------------+----------+

The list of time intervals in seconds between two consecutive wattmeter measures.
To deserialize into an exploitable numpy array, please use the function `binary_to_list <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.database.serialize.binary_to_list.html>`_.

.. tip::

    Only available for the measures taken on grid'5000.

act_wattmeter_power
-------------------

+---------------------+----------+
| act_wattmeter_power | LONGBLOB |
+---------------------+----------+

The sampled external wattmeter measurement in w.
To deserialize into an exploitable numpy array, please use the function `binary_to_list <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.database.serialize.binary_to_list.html>`_.

.. tip::

    Only available for the measures taken on grid'5000.

act_ps_dt
---------
