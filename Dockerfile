# This file is part of xrootdpyfs
# Copyright (C) 2015-2023 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

FROM almalinux:9


RUN dnf install -y git-all
RUN dnf install -y epel-release
RUN dnf update -y
# CRB (Code Ready Builder): equivalent repository to well-known CentOS PowerTools
RUN dnf install -y yum-utils
RUN dnf config-manager --set-enabled crb

RUN dnf config-manager --add-repo https://cern.ch/xrootd/xrootd.repo
RUN dnf list installed

# Install Python 3.9
RUN dnf install -y python3-devel
RUN ln -sfn /usr/bin/python3 /usr/bin/python
RUN pip3 install --upgrade pip setuptools wheel

# Install xrootd and python3-xrootd (pre-compiled version)
ARG xrootd_version=""
RUN if [ ! -z "$xrootd_version" ] ; then XROOTD_V="-$xrootd_version" ; else XROOTD_V="" ; fi && \
    echo "Will install xrootd version: $XROOTD_V (latest if empty)" && \
    dnf install -y xrootd"$XROOTD_V" python3-xrootd"$XROOTD_V"
RUN pip3 freeze

WORKDIR /code
COPY . /code

RUN pip3 install -e '.[tests]'
RUN pip3 freeze

RUN adduser --uid 1001 xrootdpyfs
RUN chown -R xrootdpyfs:xrootdpyfs /code
RUN chmod a+x /code/run-docker.sh
RUN chmod a+x /code/run-tests.sh

USER xrootdpyfs

RUN mkdir /tmp/xrootdpyfs && echo "Hello XRootD!" >> /tmp/xrootdpyfs/test.txt

# Print xrootd version
RUN XROOTD_V=`xrootd -v` && echo "xrootd version when running it: $XROOTD_V"

CMD ["bash", "/code/run-docker.sh"]
