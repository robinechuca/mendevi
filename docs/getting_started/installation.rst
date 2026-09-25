.. _simple_installation:

Simple Installation
===================

If you only want **to explore the pre-recorded data provided with mendevi, this simple installation is sufficient**. The :ref:`full_installation` is only required if you intend to perform measurements yourself.

If you want to automate the download of the available datasets, you may also install :ref:`install_transmission`.

Prerequisites
-------------

* It is preferable to install *mendevi* in a virtual environment. More details on :ref:`virtual_environment`.
* Download automation with ``transmission-daemon``. More details on :ref:`install_transmission`.

Basic Installation
------------------

To install mendevi using `PyPI <https://pypi.org/project/mendevi>`_, use ``uv pip``:

.. code:: shell

    uv pip install mendevi

Or if you want the latest:

.. code:: shell

    uv pip install git+https://framagit.org/robinechuca/mendevi.git
