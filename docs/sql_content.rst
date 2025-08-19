.. _sql_content

.. image:: https://gitlab.inria.fr/rrichard/mendevi/-/raw/main/docs/images/database.svg
    :alt: SQL database diagram

Table t_env_environement
========================

Captures the physical characteristics and configuration of a machine. This table also captures the library version for a given measurement.

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
This is human-readable text, returned by the function `get_ffmpeg_version <https://mendevi.readthedocs.io/en/latest/build/api/mendevi.context.get_ffmpeg_version.html#mendevi.context.get_ffmpeg_version>`_.

.. code-block:: python
    :linenos:

    import sqlite3
    import mendevi

