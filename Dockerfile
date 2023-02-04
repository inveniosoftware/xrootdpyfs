# This file is part of xrootdpyfs
# Copyright (C) 2015-2020 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.
#
# Dockerfile for running XRootDPyFS tests.
#
# Usage:
#   docker build -t xrootd . && docker run -h xrootdpyfs -it xrootd

FROM registry.cern.ch/inveniosoftware/almalinux:1

# Argument to install a specifc version of xrootd
ARG xrootd_version=""

# Install xrootd dependencies: https://xrootd-howto.readthedocs.io/en/latest/Compile/
RUN dnf install -y expect policycoreutils selinux-policy
RUN dnf install -y libcurl-devel libmacaroons libmacaroons-devel json-c json-c-devel uuid libuuid-devel readline-devel
RUN dnf install -y davix-libs davix-devel voms voms-devel
RUN dnf install -y cmake3 make gcc gcc-c++
RUN dnf install -y autoconf automake libtool libasan

# Install xrootd, specific version or latest
RUN if [ ! -z "$xrootd_version" ] ; then XROOTD_V="-$xrootd_version" ; else XROOTD_V="" ; fi && \
    echo "Will install xrootd version: $XROOTD_V (latest if empty)" && \
    dnf install -y xrootd"$XROOTD_V"

RUN adduser --uid 1001 xrootdpyfs

# Install Python xrootd
# Ensure that installed version of xrootd Python client is the same as the RPM package
RUN rpm --queryformat "%{VERSION}" -q xrootd
RUN XROOTD_V=`rpm --queryformat "%{VERSION}" -q xrootd` && \
    echo "RPM xrootd version installed: $XROOTD_V" && \
    pip3 install xrootd=="$XROOTD_V"

# Add sources to `code` and work there:
WORKDIR /code
COPY . /code

# FIXME REMOVE ME!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
RUN pip3 install ipdb

RUN pip3 install -e '.[docs,tests]'
RUN pip3 freeze

RUN chown -R xrootdpyfs:xrootdpyfs /code && \
    chmod a+x /code/run-docker.sh && \
    chmod a+x /code/run-tests.sh

USER xrootdpyfs

RUN mkdir /tmp/xrootdpyfs && echo "Hello XRootD!" >> /tmp/xrootdpyfs/test.txt

# Print xrootd version
RUN XROOTD_V=`xrootd -v` && echo "xrootd version when running it: $XROOTD_V"

CMD ["bash", "/code/run-docker.sh"]
