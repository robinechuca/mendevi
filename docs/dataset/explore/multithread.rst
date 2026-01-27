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

    mendevi plot multithread.db -x cores -y power -c "(profile, 'parallel' in enc_cmd)" -m encoder -e enc_scenario -s err=.err err=None

.. image:: /_static/media/multithread_cores_power.svg
    :alt: Power as a function of the logical core usage

Logical core usage as a function of the provided number of threads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    mendevi plot multithread.db -x threads -y cores -wx encoder -wy profile -c "('parallel' in enc_cmd, effort)" -m quality -f "ref_stem=='park_joy'"

.. image:: /_static/media/multithread_cores_threads.svg
    :alt: Logical core usage as a function of the provided number of threads

Relative energy as a function of the logical core usage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The figure cannot be generated directly. You must first create a template, which you can then modify.

.. code:: shell

    mendevi plot multithread.db -x cores -y act_duration -c "'parallel' in enc_cmd" -m encoder -e "(ref_stem, effort, profile, quality, hostname)" -s "supylabel\(.*\)" 'supylabel("Video encoding relative time gain")' -s "(# create legend(.|\n)*?\n\n)" '\1    cpu = np.linspace(1, 16, 100)\n    axe.plot(cpu, 1.0/cpu, "--", color="black")\n'

Then edit the function ``fill_axe`` of the just generated ``act_duration_as_a_function_of_cores.py`` file.
To do this, replace all lines in the function after ``yerr = [yerr[e] for e in errs]`` with the following code:

.. code:: python

    for x_data, y_data in zip(xerr, yerr):
        if len(x_data) < 2:
            continue
        if color_label:  # 1 thread, n videos (regression y = a*x + t0)
            _, t0 = np.polyfit(x_data, y_data, 1)
            y_data = [y/(t0*x) for x, y in zip(x_data, y_data)]
        else:  # n threads, 1 video (regression y = t1/x)
            t1 = sum(y/x for x, y in zip(x_data, y_data)) / sum(x**-2 for x in x_data)
            y_data = [y/t1 for y in y_data]
        axe.errorbar(
            x_data,
            y_data,
            color=color,
            alpha=0.5,
            fmt=marker,
            capsize=3,
            markersize=MARKERSIZE,
        )

Finally, simply run ``python act_duration_as_a_function_of_cores.py`` to generate the final figure.

.. image:: /_static/media/multithread_duration_cores.svg
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
