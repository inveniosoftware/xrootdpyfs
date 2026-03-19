# This file is part of xrootdpyfs
# Copyright (C) 2015-2026 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

FROM almalinux:9

RUN dnf update -y && \
    dnf install -y dnf-plugins-core && \
    dnf config-manager --set-enabled crb

# Python dependencies for building Python from source
RUN dnf install -y \
        epel-release \
        yum-utils \
        bzip2-devel \
        libffi-devel \
        sqlite-devel \
        python3-devel \
        python3-setuptools \
        wget && \
    dnf clean all

# XRootD dependencies
RUN dnf install -y \
        cmake \
        curl-devel \
        diffutils \
        file \
        fuse-devel \
        gcc-c++ \
        git \
        gtest-devel \
        json-c-devel \
        krb5-devel \
        libmacaroons-devel \
        libtool \
        libuuid-devel \
        libxml2-devel \
        make \
        openssl-devel \
        readline-devel \
        scitokens-cpp-devel \
        systemd-devel \
        voms-devel \
        yasm \
        zlib-devel && \
    dnf clean all

# Install Python with specified version
ARG python_version="3.14.3"
RUN wget https://www.python.org/ftp/python/${python_version}/Python-${python_version}.tgz
RUN tar xzf Python-${python_version}.tgz
RUN cd Python-${python_version} && ./configure --enable-optimizations && make altinstall
RUN ln -sfn /usr/local/bin/python${python_version%.*} /usr/bin/python

# Ensure pip is available and upgrade
RUN python${python_version%.*} -m ensurepip --upgrade
RUN python${python_version%.*} -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Add the xrootd EL10 repository
RUN dnf config-manager --add-repo https://xrootd.web.cern.ch/xrootd.repo

# Install xrootd and python3-xrootd (pre-compiled version)
ARG xrootd_version=""
RUN if [ ! -z "$xrootd_version" ] ; then XROOTD_V="-$xrootd_version" ; else XROOTD_V="" ; fi && \
    echo "Will install xrootd version: $XROOTD_V (latest if empty)" && \
    dnf install -y xrootd"$XROOTD_V" python3-xrootd"$XROOTD_V"

WORKDIR /code
COPY . /code

RUN python${python_version%.*} -m pip install --no-cache-dir -e '.[tests]'
RUN python${python_version%.*} -m pip freeze

RUN adduser --uid 1001 xrootdpyfs
RUN chown -R xrootdpyfs:xrootdpyfs /code
RUN chmod a+x /code/run-docker.sh
RUN chmod a+x /code/run-tests.sh

USER xrootdpyfs

RUN mkdir /tmp/xrootdpyfs && echo "Hello XRootD!" >> /tmp/xrootdpyfs/test.txt

# Print xrootd version
RUN XROOTD_V=`xrootd -v` && echo "xrootd version when running it: $XROOTD_V"

CMD ["bash", "/code/run-docker.sh"]
