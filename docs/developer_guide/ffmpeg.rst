.. _build_ffmpeg:

Build ffmpeg
============

The folling guide is based on the `ubuntu guide <https://trac.ffmpeg.org/wiki/CompilationGuide/Ubuntu>`_ and the `linux mint guide <https://forums.linuxmint.com/viewtopic.php?t=435381>`_.

Preparation
-----------

.. code:: shell

    # get dependencies
    sudo apt install autoconf automake build-essential cmake git-core libass-dev libfreetype6-dev libgnutls28-dev libmp3lame-dev libsdl2-dev libtool libva-dev libvdpau-dev libxcb1-dev libxcb-shm0-dev libxcb-xfixes0-dev meson ninja-build pkg-config texinfo wget yasm zlib1g-dev nasm libssl-dev
    # create directories
    rm -rf ~/ffmpeg_sources
    mkdir -pv ~/{bin,ffmpeg_sources}

Compilation & Installation
--------------------------

libx264
^^^^^^^

.. code:: shell

    cd ~/ffmpeg_sources
    git -C x264 pull 2> /dev/null || git clone --depth 1 https://code.videolan.org/videolan/x264.git
    cd x264
    PATH="$HOME/bin:$PATH" PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" ./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" --enable-static --enable-pic
    PATH="$HOME/bin:$PATH" make
    make install

libx265
^^^^^^^

.. code:: shell

    sudo apt install libnuma-dev
    cd ~/ffmpeg_sources
    wget -O x265.tar.bz2 https://bitbucket.org/multicoreware/x265_git/get/master.tar.bz2
    tar xjvf x265.tar.bz2
    cd multicoreware*/build/linux
    PATH="$HOME/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DENABLE_SHARED=off ../../source
    PATH="$HOME/bin:$PATH" make
    make install

libvpx
^^^^^^

.. code:: shell

    cd ~/ffmpeg_sources
    git -C libvpx pull 2> /dev/null || git clone --depth 1 https://chromium.googlesource.com/webm/libvpx.git
    cd libvpx
    PATH="$HOME/bin:$PATH" ./configure --prefix="$HOME/ffmpeg_build" --disable-examples --disable-unit-tests --enable-vp9-highbitdepth --as=yasm
    PATH="$HOME/bin:$PATH" make
    make install

libsvtav1
^^^^^^^^^

.. code:: shell

    # libdav1d for decoding
    cd ~/ffmpeg_sources
    git -C dav1d pull 2> /dev/null || git clone --depth 1 https://code.videolan.org/videolan/dav1d.git
    mkdir -p dav1d/build
    cd dav1d/build
    meson setup -Denable_tools=false -Denable_tests=false --default-library=static .. --prefix "$HOME/ffmpeg_build" --libdir="$HOME/ffmpeg_build/lib"
    ninja
    ninja install

    # libsvtav1 for encoding
    cd ~/ffmpeg_sources
    git -C SVT-AV1 pull 2> /dev/null || git clone https://gitlab.com/AOMediaCodec/SVT-AV1.git
    mkdir -p SVT-AV1/build
    cd SVT-AV1/build
    PATH="$HOME/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DCMAKE_BUILD_TYPE=Release -DBUILD_DEC=OFF -DBUILD_SHARED_LIBS=OFF ..
    PATH="$HOME/bin:$PATH" make
    make install

    # libaom for encoding
    cd ~/ffmpeg_sources
    git -C aom pull 2> /dev/null || git clone --depth 1 https://aomedia.googlesource.com/aom
    mkdir -p aom/build
    cd aom/build
    PATH="$HOME/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DENABLE_TESTS=OFF -DENABLE_NASM=on ..
    PATH="$HOME/bin:$PATH" make
    make install

    # librav1e for encoding
    sudo apt install rustup && rustup default stable
    cd ~/ffmpeg_sources
    git -C rav1e pull 2> /dev/null || git clone https://github.com/xiph/rav1e.git
    cd rav1e
    RUSTFLAGS="-C target-cpu=native" cargo build --release
    cargo install cargo-c
    cargo cinstall --release \
        --prefix=$HOME/ffmpeg_build \
        --libdir=$HOME/ffmpeg_build/lib \
        --includedir=$HOME/ffmpeg_build/include
    rm -v $HOME/ffmpeg_build/lib/librav1e.so*
    cp target/release/rav1e ~/bin/.

vvc
^^^

.. code:: shell

    cd ~/ffmpeg_sources
    git -C vvenc pull 2> /dev/null || git clone --depth 1 https://github.com/fraunhoferhhi/vvenc
    cd vvenc && PATH="$HOME/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF
    PATH="$HOME/bin:$PATH" make -j$(nproc)
    make -j$(nproc) install

GPU \*_nvenc \*_nvdec
^^^^^^^^^^^^^^^^^^^^^

Requires a GPU and CUDA to be installed (see :ref:`install_cuda`).
The code comes from the `ffmpeg guide <https://trac.ffmpeg.org/wiki/HWAccelIntro#NVENC>`_

.. code:: shell

    # get dependencies
    sudo apt install libc6 libc6-dev unzip libnuma1 libnuma-dev

    # chec cuda well installed
    if command -v nvidia-smi &> /dev/null; then
        # install nv-codec-headers (needed for NVENC/NVDEC support)
        cd ~/ffmpeg_sources
        git -C nv-codec-headers pull 2> /dev/null || git clone https://github.com/FFmpeg/nv-codec-headers.git
        cd nv-codec-headers
        sudo make install
        export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
    else
        echo "nvidia-smi is not working, please install cuda first"
    fi

others
^^^^^^

.. code:: shell

    sudo apt install libfdk-aac-dev libopus-dev libcaca-dev libtheora-dev libvorbis-dev


Install ffmpeg
--------------

dependencies
^^^^^^^^^^^^

.. code:: shell

    sudo apt install \
        diffutils \
        flite1-dev \
        frei0r-plugins-dev \
        ladspa-sdk \
        libbluray-dev \
        libbs2b-dev \
        libcdio-dev \
        libcdio-paranoia-dev \
        libcdparanoia-dev \
        libchromaprint-dev \
        libgme-dev \
        libgsm1-dev \
        liblzma-dev \
        libopencore-amrnb-dev \
        libopenjp2-7-dev \
        libopenmpt-dev \
        librubberband-dev \
        libshine-dev \
        libsnappy-dev \
        libsoxr-dev \
        libspeex-dev \
        libtwolame-dev \
        libv4l-dev \
        libvidstab-dev \
        libvo-amrwbenc-dev \
        libvpl-dev \
        libwebp-dev \
        libxvidcore-dev \
        libzimg-dev \
        libzvbi-dev \
        openssl

compile
^^^^^^^

.. code:: shell

    # download ffmpeg
    cd ~/ffmpeg_sources
    wget -O ffmpeg-snapshot.tar.bz2 https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2
    tar xjvf ffmpeg-snapshot.tar.bz2
    cd ffmpeg
    echo -e "$(cat VERSION) [$(date +%Y-%m-%d)] [$(cat RELEASE)] " > VERSION

    # set context
    export PATH="$HOME/bin:$PATH"
    export PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig:$PKG_CONFIG_PATH"

    # --enable-libvpl and --enable-libmfx are mutualy exclusive
    # dynamic flag declaration
    CONFIG_FLAGS="
        --prefix=\"$HOME/ffmpeg_build\"
        --pkg-config-flags=\"--static\"
        --extra-cflags=\"-I$HOME/ffmpeg_build/include\"
        --extra-ldflags=\"-L$HOME/ffmpeg_build/lib\"
        --extra-libs=\"-lpthread -lm\"
        --ld=\"g++\"
        --bindir=\"$HOME/bin\"

        --enable-chromaprint
        --enable-frei0r
        --enable-gpl
        --enable-ladspa
        --enable-libaom
        --enable-libass
        --enable-libbluray
        --enable-libbs2b
        --enable-libcaca
        --enable-libcdio
        --enable-libdav1d
        --enable-libdrm
        --enable-libfdk-aac
        --enable-libflite
        --enable-libfontconfig
        --enable-libfreetype
        --enable-libfribidi
        --enable-libgme
        --enable-libgsm
        --enable-libharfbuzz
        --enable-libmp3lame
        --enable-libopenmpt
        --enable-libopus
        --enable-libpulse
        --enable-librav1e
        --enable-librubberband
        --enable-librubberband
        --enable-libshine
        --enable-libsnappy
        --enable-libsoxr
        --enable-libspeex
        --enable-libsvtav1
        --enable-libtheora
        --enable-libtwolame
        --enable-libvidstab
        --enable-libvo-amrwbenc
        --enable-libvorbis
        --enable-libvpl
        --enable-libvpx
        --enable-libvvenc
        --enable-libwebp
        --enable-libx264
        --enable-libx265
        --enable-libxml2
        --enable-libxvid
        --enable-libzimg
        --enable-libzvbi
        --enable-nonfree
        --enable-opengl
        --enable-openssl
        --enable-vaapi
        --enable-version3
    "
    # add --enable-cuda-nvcc
    if command -v nvidia-smi &> /dev/null; then
        CONFIG_FLAGS="$CONFIG_FLAGS --enable-cuda-nvcc --enable-ffnvcodec"
    fi

    # compilation and installation
    eval ./configure $CONFIG_FLAGS
    PATH="$HOME/bin:$PATH" make -j$(nproc) && make -j$(nproc) install && hash -r

    # linkage
    cp ~/ffmpeg_build/bin/x265 ~/bin
    cp ~/ffmpeg_build/bin/SvtAv1EncApp ~/bin
    cd ~/bin
    # cp ffmpeg /usr/bin/. && cp ffprobe /usr/bin/.