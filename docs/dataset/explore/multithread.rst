.. _multithread_datset:

Multithread Dataset
===================

It allows to perform an "experimental analysis of the impact of multi-threading on video encoding energy consumption".

Download
--------

.. code:: shell

    mendevi download multithread.db.xz.torrent

* `multithread.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/multithread.json.xz?inline=false>`_ (1.2 Mo).
* `multithread.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/multithread.db.xz.torrent?inline=false>`_ (5.8 Go).

Plots
-----

Power as a function of the logical core usage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<multithread.db>' -x cores -y power -c '(profile, hostname)' -m encoder

.. image:: /_static/media/multithread_cores_power.svg
    :alt: Power as a function of the logical core usage

Logical core usage as a function of the provided number of threads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<multithread.db>' -x threads -y cores -wx encoder -wy profile -c effort -m quality -f '"aerial" in name'

.. image:: /_static/media/multithread_cores_threads.svg
    :alt: Logical core usage as a function of the provided number of threads

Final energy as a function of the provided number of threads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot '<multithread.db>' -x threads -y energy -wx encoder -wy profile -c effort -m quality -e '(threads, name)'

.. image:: /_static/media/multithread_energy_threads.svg
    :alt: Final energy as a function of the provided number of threads

Conclusion
----------

The more cores used, the faster the encoding, and therefore the less significant the static power consumption. The gain is therefore very high for a small number of threads. However, this gain becomes less significant when exceeding 8 threads. In addition, bit rate distortion decreases with the number of threads due to tiling. Thus, 8 threads seems optimal.

Reproduce
---------

.. code:: shell

    mendevi prepare -p sd netflix_aerial.mp4
    mendevi prepare -p fhd netflix_aerial.mp4

    mendevi encode reference* -e fast -e medium -n2 -t1 -t2 -t3 -t4 -t5 -t6 -t7 -t8 -t9 -t10 -t11 -t12 -t13 -t14 -t15 -t16

    mendevi probe reference* sample*
