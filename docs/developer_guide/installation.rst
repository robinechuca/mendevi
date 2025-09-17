.. _full_installation:

Full Installation
=================

.. _Debian Ubuntu Mint:
.. _RHEL CentOS Fedora:
.. _Arch Manjaro:
.. _OpenSUSE:
.. _Linux Installation:
.. _FreeBSD Installation:
.. _macOS Installation:
.. _Windows Installation:


.. _virtual_environement:

Virtual Environement
--------------------

It is preferable to install *mendevi* in a virtual environment. Please refer to the `pyenv main page <https://github.com/pyenv/pyenv>`_. It is possible to use ``python3-venv`` or ``conda`` as well.

.. _install_pyenv:

Install pyenv
^^^^^^^^^^^^^

First install the `python dependencies <https://github.com/pyenv/pyenv/wiki#suggested-build-environment>`_ then install pyenv.

.. tab:: Linux

    .. tab:: Debian Ubuntu Mint

        .. code:: shell

            sudo apt install libedit-dev libncurses5-dev
            sudo apt install build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev curl git libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

    .. tab:: RHEL CentOS Fedora

        .. code:: shell

            sudo dnf install openssl11-devel --allowerasing
            dnf install gcc make patch zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz-devel

    .. tab:: Arch Manjaro

        .. code:: shell

            yay -S ncurses5-compat-libs

    .. code:: shell

        curl https://pyenv.run | bash
        CONTENT=$'export PYENV_ROOT="$HOME/.pyenv"\ncommand -v pyenv > /dev/null || export PATH="$PYENV_ROOT/bin:$PATH"\neval "$(pyenv init -)"\neval "$(pyenv virtualenv-init -)"'
        grep -q "$CONTENT" ~/.bashrc || echo "$CONTENT" >> ~/.bashrc
        source ~/.bashrc

.. tab:: macOS

    You could install dependencies by using `Homebrew <https://brew.sh>`_.

    .. code:: shell

        brew install ncurses
        brew install openssl readline sqlite3 xz zlib tcl-tk
        brew install pyenv

.. tab:: Windows

    .. warning:: Windows is crap, so be prepared for a tedious and buggy installation! You should forget Microchiotte-Windaube and go straight to Linux before you pull out all your hair!

    Good luck with the `official guide <https://github.com/pyenv-win/pyenv-win>`_.

If it fails, `this debug link <https://github.com/pyenv/pyenv/wiki/Common-build-problems>`_ may help you.

Configure pyenv
^^^^^^^^^^^^^^^

Create the virtual environement.

.. code:: shell

    pyenv update
    env PYTHON_CONFIGURE_OPTS="--enable-shared --enable-optimizations --with-lto" PYTHON_CFLAGS='-march=native -mtune=native' \
    pyenv install -v 3.13
    pyenv virtualenv 3.13 mendevi
    pyenv activate mendevi
    pip install uv


.. _dependencies:

Dependencies
------------

.. _install_ffmpeg:

ffmpeg
^^^^^^

If you want the latest version, please build it :ref:`build_ffmpeg`.

*mendevi* has hard dependency on the FFmpeg package. You should install it first, please refer to the `FFmpeg download page <https://ffmpeg.org/download.html>`_.

.. tab:: Linux

    .. tab:: Debian Ubuntu Mint

        .. code:: shell

            sudo apt install ffmpeg
            sudo apt install python-dev-is-python3 pkg-config
            sudo apt install libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev libswresample-dev libavfilter-dev

    .. tab:: RHEL CentOS Fedora

        .. code:: shell

            sudo dnf install ffmpeg

    .. tab:: Arch Manjaro

        .. code:: shell

            sudo pacman -S ffmpeg

    .. tab:: OpenSUSE

        .. code:: shell

            sudo zypper install ffmpeg

.. tab:: FreeBSD

    .. code:: shell

        sudo pkg install ffmpeg

.. tab:: macOS

    You could install the FFmpeg by using `Homebrew <https://brew.sh>`_.

    .. code:: shell

        brew install ffmpeg pkg-config

.. tab:: Windows

    .. warning:: I refuse to believe that you have gone through the previous steps. As you are stubborn and stupid, I must remind you that the game is not yet won! It is still not too late to listen to the voice of wisdom, which is telling you to get rid of this massive piece of Windows shit for ever.

    It is important to configure your environement variable to hook ffmpeg to *mendevi*. You can try to follow `this guide <https://www.geeksforgeeks.org/how-to-install-ffmpeg-on-windows>`_ for example.

.. _install_lshw:

lshw
^^^^

To get the full environement information, *mendevi* use tha system package ``lshw``.

.. tab:: Linux

    .. tab:: Debian Ubuntu Mint

        .. code:: shell

            sudo apt install lshw

    .. tab:: RHEL CentOS Fedora

        .. code:: shell

            sudo dnf install lshw

    .. tab:: Arch Manjaro

        .. code:: shell

            sudo pacman -S lshw

.. _install_perf:

perf
^^^^

To access the RAPL sensors.

.. tab:: Linux

    .. tab:: Debian Ubuntu Mint

        .. code:: shell

            if ! sudo apt install -y linux-perf; then
                sudo apt install -y linux-tools-common linux-tools-generic linux-tools-$(uname -r)
            fi

    .. tab:: RHEL CentOS Fedora

        .. code:: shell

            sudo dnf install perf

    .. tab:: Arch Manjaro

        .. code:: shell

            sudo pacman -S perf

.. _install_pyav:

pyav (optional)
^^^^^^^^^^^^^^^

Although it is installed automatically, it is better to install **av** manually to avoid redundancy with ffmpeg. Please refer to the `PyAv installation guide <https://pyav.org/docs/develop/overview/installation.html>`_.

.. tab:: Linux

    .. code:: shell

        uv pip -v install av --no-binary av

.. tab:: FreeBSD

    .. code:: shell

        uv pip -v install av --no-binary av

.. tab:: macOS

    On **MacOS** you may have issues with regards to Python expecting gcc but finding clang. Try to export the following before installation:

    .. code:: shell

        export ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future
        uv pip -v install av --no-binary av

.. tab:: Windows

    .. warning:: I see that you insist on using Windows, this step is the most critical, good luck!

    On **Windows** you must build from source in order to indicate the location of ffmpeg, pleas follow the `PyAv windows installation guide <https://pyav.org/docs/develop/overview/installation.html#windows>`_ and good luck!

.. _install_cuda:

cuda (optional)
^^^^^^^^^^^^^^^

If you have a GPU, please install CUDA or ROC then follow the `PyTorch installation guide <https://pytorch.org>`_. Without CUDA or ROC, the software is not able to use the GPU (CPU only).

.. tab:: Linux

    Follow the official `NVIDIA CUDA Installation Guide for Linux <https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html>`_.

.. tab:: FreeBSD

    It is not well supproted, you can try to follow `this bsd link <https://gist.github.com/Mostly-BSD/4d3cacc0ee2f045ed8505005fd664c6e>`_.

.. tab:: macOS

    Follow the `NVIDIA CUDA Installation Guide for Mac OS X <https://docs.nvidia.com/cuda/archive/10.2/cuda-installation-guide-mac-os-x/index.html>`_.

.. tab:: Windows

    .. warning:: Windows is crap, so be prepared for a tedious and buggy installation! You should forget Microchiotte-Windaube and go straight to Linux before you pull out all your hair!

    It is important to configure your environement variable to hook cuda to PyTorch.
    Good luck with the `official guide <https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/index.html>`_.

.. _install_vmaf:

vamf (optional)
^^^^^^^^^^^^^^^

If you want to have acces to the `Netflix VMAF quality metric <https://wiki.x266.mov/docs/metrics/VMAF>`_, please install it!

.. tab:: Linux

    .. tab:: Debian Ubuntu Mint

        .. code:: shell

            sudo apt install meson nasm
            git clone https://github.com/Netflix/vmaf/ ~/vmaf_git
            cd ~/vmaf_git
            meson setup libvmaf libvmaf/build --buildtype release -Denable_float=true
            sudo ninja -vC libvmaf/build install
            cd -
            rm -rf ~/vmaf_git


Installation
------------

Basic Installation
^^^^^^^^^^^^^^^^^^

.. note::

    The following instructions will install a minimal version of *mendevi*.
    See :ref:`building_from_source` for a complete installation including the documentation and the tests.

To install the lastest development version, use ``uv pip``:

.. code:: shell

    uv pip install git+https://gitlab.inria.fr/rrichard/mendevi.git

.. _building_from_source:

Building From Source (For devellopers)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To install the lastest development version from `GitLab <https://gitlab.inria.fr/rrichard/mendevi>`_ source, clone mendevi using ``git`` and install it using ``uv pip``:

.. code:: shell

    git clone https://gitlab.inria.fr/rrichard/mendevi.git ~/mendevi_git
    cd ~/mendevi_git
    pyenv activate mendevi  # to be sure to be in a virtual env
    uv pip -v install --editable .[doc,test]
    mendevi test  # to test if the installation is ok
.. pip uninstall typing_extensions to debug attribute '__default__' of 'typing.ParamSpec' objects is not writable

You can now also compile documentation locally :ref:`documentation` and run the benchmark :ref:`testing` (after the previous step).


.. _documentation:

Build Documentation
-------------------

You can compile the documentation yourself after :ref:`full_installation` by simply typing ``mendevi doc`` or:

.. code:: shell

    cd docs/ && make clean && make html && cd -
    firefox docs/build/html/index.html
