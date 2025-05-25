#!/usr/bin/env bash

# Fail on error
set -e

# Install DPDK
function dpdk {
    # Check if DPDK is already installed
    if [ -d /usr/dpdk ]; then
        echo "DPDK is already installed."
        return
    fi

    echo "Installing dependencies..."
    apt update -y && apt install -y \
        wget \
        xz-utils \
        meson \
        libnuma-dev \
        libssl-dev \
        python3-pyelftools

    echo "Downloading DPDK sources..."
    mkdir -p /usr/src
    cd /usr/src/
    wget https://fast.dpdk.org/rel/dpdk-24.11.1.tar.xz
    tar xf dpdk-24.11.1.tar.xz
    export DPDK_DIR=/usr/src/dpdk-stable-24.11.1
    export DPDK_BUILD_DIR=$DPDK_DIR/build
    export DPDK_OUTPUT_DIR=$DPDK_BUILD_DIR/dpdk_out
    export DPDK_INSTALL_DIR=/usr/dpdk

    cd $DPDK_DIR

    echo "Building DPDK..."
    meson --prefix=$DPDK_INSTALL_DIR $DPDK_DIR $DPDK_BUILD_DIR
    ninja -C $DPDK_BUILD_DIR
    ninja -C $DPDK_BUILD_DIR install

    echo "Building DPDK deb package..."
    mkdir -p $DPDK_OUTPUT_DIR/usr
    mv $DPDK_INSTALL_DIR $DPDK_OUTPUT_DIR/usr
    mkdir -p $DPDK_OUTPUT_DIR/DEBIAN
    printf 'Package: libdpdk-dev\nVersion: 24.11.1\nMaintainer: Robert-Ioan Constantinescu\nArchitecture: amd64\nDescription: DPDK required by OVS-DPDK\n' > $DPDK_OUTPUT_DIR/DEBIAN/control
    printf '#!/usr/bin/env bash\n\nldconfig' > $DPDK_OUTPUT_DIR/DEBIAN/postinst
    chmod +x $DPDK_OUTPUT_DIR/DEBIAN/postinst
    mkdir -p $DPDK_OUTPUT_DIR/etc/ld.so.conf.d
    printf '/usr/dpdk/lib/x86_64-linux-gnu' > $DPDK_OUTPUT_DIR/etc/ld.so.conf.d/dpdk.conf
    mkdir -p $DPDK_OUTPUT_DIR/usr/lib/x86_64-linux-gnu/pkgconfig
    cp $DPDK_OUTPUT_DIR/usr/dpdk/lib/x86_64-linux-gnu/pkgconfig/* \
       $DPDK_OUTPUT_DIR/usr/lib/x86_64-linux-gnu/pkgconfig/
    dpkg-deb --build $DPDK_OUTPUT_DIR libdpdk-dev.deb

    echo "Installing DPDK deb package..."
    apt install $DPDK_DIR/libdpdk-dev.deb
}

dpdk

