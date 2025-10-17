PUBLIC MENDEVI DATASETS
=======================

The structure of the datasets is described in detail in `the online documentation <https://mendevi.readthedocs.io/latest/dataset/structure.html>`_ or in the `documentation source file <https://gitlab.inria.fr/rrichard/mendevi/-/tree/main/docs/dataset/structure>`_.

The description of the dataset content is also available `online <https://mendevi.readthedocs.io/latest/dataset/explore.html>`_ or in the `source code <https://gitlab.inria.fr/rrichard/mendevi/-/tree/main/docs/dataset/explore>`_.


How can I retrieve them?
------------------------

Since they are several GB in size, they are distributed via the torrent protocol.
Simply open the torrent file with software such as `transmission <https://transmissionbt.com/>`_ to download the database.

Then decompress the file with ``xz -dv *.xz``. That's it!


How to publish your own dataset?
--------------------------------

After generating a database by following `these steps <https://mendevi.readthedocs.io/latest/getting_started/measure.html>`_, you will obtain a SQL file named ``mendevi.db``.

1) To generate the json file (``mendevi.json``), simply type ``mendevi json mendevi.db``.

2) You must then compress these raw files by typing ``xz -vve9T1 --lzma2=dict=1GiB mendevi.json`` and ``xz -vvke9T1 --lzma2=dict=1GiB mendevi.xz``.

3) Rename files with a meaningful name, for example ``mv mendevi.json.xz coucougnoux.json.xz && `mv mendevi.db.xz coucougnoux.db.xz``

4) Create a toorent file with
