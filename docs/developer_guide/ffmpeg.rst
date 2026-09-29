.. _build_ffmpeg:

Build ffmpeg
============

Allows you to compile ffmpeg **on Debian** with the latest versions of video encoders.

The following guide is based on the `official debian and ubuntu guide <https://trac.ffmpeg.org/wiki/CompilationGuide/Ubuntu>`_, and the `linux mint guide <https://forums.linuxmint.com/viewtopic.php?t=435381>`_.

Preparation
-----------

.. code:: shell

    # get dependencies
    sudo apt install \
        autoconf automake build-essential cmake git-core diffutils flite1-dev frei0r-plugins-dev gcc git ladspa-sdk libass-dev libbluray-dev libbs2b-dev libcdio-dev libcdio-paranoia-dev libcdparanoia-dev libchromaprint-dev libfreetype6-dev libgme-dev libgnutls28-dev libgsm1-dev liblzma-dev libmp3lame-dev libopencore-amrnb-dev libopenjp2-7-dev libopenmpt-dev librubberband-dev libsdl2-dev libshine-dev libsnappy-dev libsoxr-dev libspeex-dev libssl-dev libtool libtwolame-dev libv4l-dev libva-dev libvdpau-dev libvidstab-dev libvo-amrwbenc-dev libvpl-dev libwebp-dev libxcb-shm0-dev libxcb-xfixes0-dev libxcb1-dev libxvidcore-dev libzimg-dev libzvbi-dev meson nasm ninja-build texinfo wget yasm zlib1g-dev

    # create directories
    rm -rf $HOME/ffmpeg_sources
    mkdir -pv $HOME/{bin,ffmpeg_sources}

    # optimized compilation
    export CFLAGS="-O2 -march=native -mtune=native"
    export CXXFLAGS="$CFLAGS"

Compilation & Installation
--------------------------

libx264 and libopenh264
^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    # libx264
    # Instead of the following code, you can do "sudo apt install libx264-dev".
    cd $HOME/ffmpeg_sources
    git -C x264 pull 2> /dev/null || git clone --depth 1 https://code.videolan.org/videolan/x264.git
    cd x264
    PATH="$HOME/bin:$PATH" PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" \
        ./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" --enable-static --enable-pic --extra-cflags="$CFLAGS"
    PATH="$HOME/bin:$PATH" make
    make install

    # libopenh264
    # Instead of the following code, you can do "sudo apt install libopenh264-dev".
    cd $HOME/ffmpeg_sources
    git -C openh264 pull 2> /dev/null || git clone --depth 1 https://github.com/cisco/openh264.git
    cd openh264
    ARCH=$(uname -m)
    PATH="$HOME/bin:$PATH" make OS=linux ARCH="$ARCH"
    make install PREFIX="$HOME/ffmpeg_build"
    rm $HOME/ffmpeg_build/lib/libopenh264.so*  # to force the static build otherwise it will failed on dynamic

libx265
^^^^^^^

.. code:: shell

    # Instead of the following code, you can do "sudo apt install libx265-dev".
    sudo apt install libnuma-dev
    cd $HOME/ffmpeg_sources
    wget -O x265.tar.bz2 https://bitbucket.org/multicoreware/x265_git/get/master.tar.bz2
    tar xjvf x265.tar.bz2
    cd multicoreware*/build/linux
    PATH="$HOME/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DENABLE_SHARED=off -DCMAKE_C_FLAGS="$CFLAGS" -DCMAKE_CXX_FLAGS="$CXXFLAGS" ../../source
    PATH="$HOME/bin:$PATH" make
    make install

libvpx
^^^^^^

.. code:: shell

    # Instead of the following code, you can do "sudo apt install libvpx-dev".
    cd $HOME/ffmpeg_sources
    git -C libvpx pull 2> /dev/null || git clone --depth 1 https://chromium.googlesource.com/webm/libvpx.git
    cd libvpx
    PATH="$HOME/bin:$PATH" ./configure --prefix="$HOME/ffmpeg_build" --disable-examples --disable-unit-tests --enable-vp9-highbitdepth --as=yasm --extra-cflags="$CFLAGS" --extra-cxxflags="$CXXFLAGS"
    PATH="$HOME/bin:$PATH" make
    make install

libdav1d, libsvtav1, libaom and librav1e
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: shell

    # libdav1d for decoding
    # Instead of the following code, you can do "sudo apt install libdav1d-dev".
    cd $HOME/ffmpeg_sources
    git -C dav1d pull 2> /dev/null || git clone --depth 1 https://code.videolan.org/videolan/dav1d.git
    mkdir -p dav1d/build
    cd dav1d/build
    meson setup -Denable_tools=false -Denable_tests=false --default-library=static --optimization=3 -Db_lto=true -Dc_args="$CFLAGS" -Dcpp_args="$CXXFLAGS" .. --prefix "$HOME/ffmpeg_build" --libdir="$HOME/ffmpeg_build/lib"
    ninja
    ninja install

    # libsvtav1 for encoding
    # Instead of the following code, you can do "sudo apt install libsvtav1enc-dev".
    cd $HOME/ffmpeg_sources
    git -C SVT-AV1 pull 2> /dev/null || git clone --depth 1 https://gitlab.com/AOMediaCodec/SVT-AV1.git
    mkdir -p SVT-AV1/build
    cd SVT-AV1/build
    PATH="$HOME/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DCMAKE_BUILD_TYPE=Release -DBUILD_DEC=OFF -DBUILD_SHARED_LIBS=OFF -DCMAKE_C_FLAGS="$CFLAGS" -DCMAKE_CXX_FLAGS="$CXXFLAGS" ..
    PATH="$HOME/bin:$PATH" make
    make install

    # libaom for encoding
    # Instead of the following code, you can do "sudo apt install libaom-dev".
    cd $HOME/ffmpeg_sources
    git -C aom pull 2> /dev/null || git clone --depth 1 https://aomedia.googlesource.com/aom
    mkdir -p aom/build
    cd aom/build
    PATH="$HOME/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DENABLE_TESTS=OFF -DENABLE_NASM=on -DCMAKE_C_FLAGS="$CFLAGS" -DCMAKE_CXX_FLAGS="$CXXFLAGS" ..
    PATH="$HOME/bin:$PATH" make
    make install

    # librav1e for encoding
    # Instead of the following code, you can do "sudo apt install librav1e-dev".
    if apt-cache search --names-only "^rustup$" | grep -q "^rustup "; then
        sudo apt install rustup
    else
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
        source "$HOME/.cargo/env"
    fi
    rustup default stable
    cd $HOME/ffmpeg_sources
    git -C rav1e pull 2> /dev/null || git clone --depth 1 https://github.com/xiph/rav1e.git
    cd rav1e
    RUSTFLAGS="-C target-cpu=native" cargo build --release
    cargo install cargo-c
    cargo cinstall --release \
        --prefix=$HOME/ffmpeg_build \
        --libdir=$HOME/ffmpeg_build/lib \
        --includedir=$HOME/ffmpeg_build/include
    rm -v $HOME/ffmpeg_build/lib/librav1e.so*
    cp target/release/rav1e $HOME/bin/.

av2
^^^

It is not yet linked to ffmpeg. (experimental)

.. code:: shell

    cd $HOME/ffmpeg_sources
    git -C avm pull 2> /dev/null || git clone --depth 1 https://github.com/AOMediaCodec/avm
    mkdir -p avm/build
    cd avm/build
    PATH="$HOME/bin:$PATH" cmake .. -G "Unix Makefiles" \
        -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DCMAKE_C_FLAGS="$CFLAGS" -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DBUILD_SHARED_LIBS=1 -DCONFIG_AV2_ENCODER=1 -DCONFIG_AV2_DECODER=1 -DENABLE_DOCS=0
    PATH="$HOME/bin:$PATH" make
    make install
    cp avmenc avmdec "$HOME/bin/"

vvc
^^^
.. code:: shell

    cd $HOME/ffmpeg_sources
    git -C vvenc pull 2> /dev/null || git clone --depth 1 https://github.com/fraunhoferhhi/vvenc
    cd vvenc
    PATH="$HOME/bin:$PATH" cmake .. -G "Unix Makefiles" \
        -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCMAKE_C_FLAGS="$CFLAGS" -DCMAKE_CXX_FLAGS="$CXXFLAGS"
    PATH="$HOME/bin:$PATH" make
    make install

GPU \*_nvenc \*_nvdec
^^^^^^^^^^^^^^^^^^^^^

Requires a NVIDIA GPU and CUDA to be installed (see :ref:`install_cuda`).
The code comes from the `ffmpeg guide <https://trac.ffmpeg.org/wiki/HWAccelIntro#NVENC>`_.
If it fails, `this tutorial <https://www.cyberciti.biz/faq/how-to-install-ffmpeg-with-nvidia-gpu-acceleration-on-linux/>`_ may help you.

.. note::

    Only a few GPU supports all codecs. `These are the supported codecs <https://developer.nvidia.com/video-encode-decode-support-matrix>`_.

.. code:: shell

    # get dependencies
    sudo apt install libc6 libc6-dev unzip libnuma1 libnuma-dev

    # check if cuda is well installed
    if command -v nvidia-smi &> /dev/null; then
        # install nv-codec-headers (needed for NVENC/NVDEC support)
        cd $HOME/ffmpeg_sources
        git -C nv-codec-headers pull 2> /dev/null || git clone --depth 1 https://github.com/FFmpeg/nv-codec-headers.git
        cd nv-codec-headers
        sudo make install
        export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
    else
        echo "nvidia-smi is not working, please install cuda first"
    fi

GPU \*_amf d3d11va
^^^^^^^^^^^^^^^^^^

Requires a AMD GPU (see :ref:`install_amf`).
The code comes from the `amf wiki <https://github.com/GPUOpen-LibrariesAndSDKs/AMF/wiki/Build-FFmpeg-with-AMF-Support>`_.

.. code:: shell

    cd $HOME/ffmpeg_sources
    git -C AMF pull 2> /dev/null || git clone --depth 1 https://github.com/GPUOpen-LibrariesAndSDKs/AMF.git
    mkdir -p /usr/local/include/AMF
    cp -r AMF/amf/public/include/* /usr/local/include/AMF/

vaapi: integrated intel GPU chip
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Not all codecs are supported, it really depends on the CPUs. Here is a `non-exhaustive list <https://github.com/intel/media-driver>`_.

.. code:: shell

    if [ -e "/dev/dri/renderD128" ]; then
        sudo apt install intel-media-va-driver-non-free vainfo intel-gpu-tools
    else
        echo "It appears that vaapi is not supported by this hardware."
    fi

others
^^^^^^

.. code:: shell

    sudo apt install libfdk-aac-dev libopus-dev libcaca-dev libtheora-dev libvorbis-dev

Install ffmpeg
--------------

preparation
^^^^^^^^^^^

.. code:: shell

    # download ffmpeg (see https://ffmpeg.org/releases/)
    cd $HOME/ffmpeg_sources
    wget -O ffmpeg-snapshot.tar.xz https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz
    mkdir -p ffmpeg && tar -xvf ffmpeg-snapshot.tar.xz -C ffmpeg --strip-components=1
    cd ffmpeg
    # echo -e "$(cat VERSION) [$(date +%Y-%m-%d)] [$(cat RELEASE)]" > VERSION

    # set context
    export PATH="$HOME/bin:$PATH"
    export PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig:$PKG_CONFIG_PATH"
    export LDFLAGS="-L$HOME/ffmpeg_build/lib -Wl,-rpath,$HOME/bin"  # for pyav

    # --enable-libvpl and --enable-libmfx are mutually exclusive, both are for *_qsv codecs
    # dynamic flag declaration
    CONFIG_FLAGS="
        --prefix=\"$HOME/ffmpeg_build\"
        --pkg-config-flags=\"--static\"
        --extra-cflags=\"-I$HOME/ffmpeg_build/include\"
        --extra-ldflags=\"-L$HOME/ffmpeg_build/lib\"
        --extra-libs=\"-lpthread -lm\"
        --ld=\"g++\"
        --bindir=\"$HOME/bin\"
        --enable-shared

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
        --enable-libopenh264
        --enable-libopenmpt
        --enable-libopus
        --enable-libpulse
        --enable-librav1e
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

        --enable-libvpl
        --disable-libmfx
    "
    # add --enable-cuda-nvcc
    if command -v nvidia-smi &> /dev/null; then
        CONFIG_FLAGS="$CONFIG_FLAGS --enable-cuda-nvcc --enable-ffnvcodec"
    fi
    # add --enable-amf
    if [ -d "/usr/local/include/AMF" ]; then
        CONFIG_FLAGS="$CONFIG_FLAGS --enable-amf"
    fi

compilation
-----------

.. code:: shell

    # compilation and installation
    CONFIG_COMPILE_FLAGS="$CONFIG_FLAGS --extra-cflags='$CFLAGS' --extra-cxxflags='$CXXFLAGS'"
    eval ./configure $CONFIG_COMPILE_FLAGS
    make && make install && hash -r

    # linkage
    cp $HOME/ffmpeg_build/bin/x265 $HOME/bin
    cp $HOME/ffmpeg_build/bin/SvtAv1EncApp $HOME/bin
    cp $HOME/ffmpeg_build/lib/lib{avcodec,avdevice,avfilter,avformat,avutil,swresample,swscale}.so* $HOME/bin

    CONTENT=$'export PATH=$HOME/bin:$PATH'
    grep -q "$CONTENT" $HOME/.bashrc || echo "$CONTENT" >> $HOME/.bashrc
    source $HOME/.bashrc

    # cd $HOME/bin && sudo cp ff* /usr/bin/.
    # uv pip install -v av --no-binary av --no-cache
