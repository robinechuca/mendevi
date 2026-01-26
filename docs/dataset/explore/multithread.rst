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

    mendevi plot multithread.db -x cores -y power -c '(profile, hostname)' -m encoder -e enc_scenario -s err=.err err=None
    mendevi plot multithread.db -x cores -y power -c "(profile, enc_cmd.startswith('parallel'))" -m encoder -e enc_scenario -s err=.err err=None

.. image:: /_static/media/multithread_cores_power.svg
    :alt: Power as a function of the logical core usage

Logical core usage as a function of the provided number of threads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot multithread.db -x threads -y cores -wx encoder -wy profile -c effort -m quality -f "ref_stem=='park_joy'"

.. image:: /_static/media/multithread_cores_threads.svg
    :alt: Logical core usage as a function of the provided number of threads

Final energy as a function of the provided number of threads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot multithread.db -x threads -y energy -wx encoder -wy profile -c effort -m quality -e '(threads, name)'

.. image:: /_static/media/multithread_energy_threads.svg
    :alt: Final energy as a function of the provided number of threads

Conclusion
----------

The more cores used, the faster the encoding, and therefore the less significant the static power consumption. The gain is therefore very high for a small number of threads. However, this gain becomes less significant when exceeding 8 threads. In addition, bit rate distortion decreases with the number of threads due to tiling. Thus, 8 threads seems optimal.

Reproduce
---------

Create the file ``callback.py`` with the following content:

.. code:: python

    """Helper for mendevi multithread database."""

    import pathlib
    import shlex

    from mendevi.cmd import CmdFFMPEG
    from mendevi.encode import get_transcode_cmd


    def n_threads_to_multiple_encodings(cmd: CmdFFMPEG, **kwargs) -> str:
        """Transform a single encoding on n threads, to n encoding on 1 thread."""
        # change the command for a single thread encoding
        src, dst = cmd.video, pathlib.Path(cmd.output[0])  # input / output video file
        loop = kwargs.pop("threads")  # number parallel encoding
        cmd = get_transcode_cmd(src, dst, **kwargs, threads=1)

        # duplicate the command n times, with different output
        for file in dst.parent.iterdir():
            if file.stem.startswith("bis_"):
                file.unlink()
        cmds = [cmd]
        for i in range(1, loop):
            new_cmd = cmd.copy()
            new_cmd.output = [str((dst.parent / f"bis_{i}").with_suffix(dst.suffix))]
            cmds.append(new_cmd)

        # merge together
        return f"parallel -j{loop} ::: {' '.join(shlex.quote(str(c)) for c in cmds)}"

It requires the linux tool ``sudo apt install parallel``.

Then in a terminal, run:

.. code:: shell

    for video in ctc/*.mkv; do
        mendevi prepare $video -p sd
        mendevi prepare $video -p fhd
    done
    
    mendevi encode -n2 -e fast -e medium -c libopenh264 -c librav1e -c libsvtav1 -c libvpx-vp9 -c libx264 -c libx265 -c vvc -t1 -t2 -t3 -t4 -t5 -t6 -t7 -t8 -t9 -t10 -t11 -t12 -t13 -t14 -t15 -t16 -d n_thread_1_vid.db reference*
    mendevi encode -n2 -e fast -e medium -c libopenh264 -c librav1e -c libsvtav1 -c libvpx-vp9 -c libx264 -c libx265 -c vvc -t1 -t2 -t3 -t4 -t5 -t6 -t7 -t8 -t9 -t10 -t11 -t12 -t13 -t14 -t15 -t16 --callback callback.py -d 1_thread_n_vid.db reference*
    mendevi merge n_thread_1_vid.db 1_thread_n_vid.db && mv merge_n_thread_1_vid_1_thread_n_vid.db multithread.db
    
    mendevi probe -d multithread.db reference* sample*
