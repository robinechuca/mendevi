.. _multithread_datset:

Multithread Dataset
===================

It allows to perform an "experimental analysis of the impact of multi-threading on video encoding energy consumption".

Download
--------

* `multithread.json.xz <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/multithread.json.xz>`_ (1.2 Mo).
* `multithread.db.xz.torrent <https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/dataset/multithread.db.xz.torrent>`_ (5.8 Go).

Plots
-----

Power as a function of the logical core usage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot multithread.db -x cores -y power -c '(profile, hostname)' -m encoder


.. image:: /_static/media/multithread_cores_power.svg
    :alt: Power as a function of the logical core usage


Logical core usage as a function of the provided number of threads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot multithread.db -x threads -y cores -wx encoder -wy profile -c effort -m quality -f '"aerial" in name'


.. image:: /_static/media/multithread_cores_threads.svg
    :alt: Logical core usage as a function of the provided number of threads


Final energy as a function of the provided number of threads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot multithread.db -x threads -y energy -wx encoder -wy profile -c effort -m quality -f '"aerial" in name'


.. image:: /_static/media/multithread_energy_threads.svg
    :alt: Final energy as a function of the provided number of threads
