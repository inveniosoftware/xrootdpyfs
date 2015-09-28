# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.
#
# Dockerfile for running XRootDFS tests.
#
# Usage:
#   docker build -t xrootd . && docker run -h xrootdfs -it xrootd

FROM centos:7

# Install xrootd
RUN rpm -Uvh http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

RUN yum install -y xrootd xrootd-server xrootd-client xrootd-client-devel xrootd-python git

RUN yum install -y python-pip

RUN adduser --uid 1001 xrootdfs

# Install some prerequisites ahead of `setup.py` in order to profit
# from the docker build cache:
RUN pip install --upgrade pip setuptools
RUN pip install ipython \
                pep257 \
                coverage \
                pytest \
                pytest-pep8 \
                pytest-cov \
                isort \
                mock \
                Sphinx
RUN pip install fs

# Add sources to `code` and work there:
WORKDIR /code
COPY . /code

RUN pip install -e .

RUN chown -R xrootdfs:xrootdfs /code && chmod a+x /code/run-docker.sh && chmod a+x /code/run-tests.sh

USER xrootdfs

RUN mkdir /tmp/xrootdfs && echo "Hello XRootD!" >> /tmp/xrootdfs/test.txt

# Print xrootd version
RUN xrootd -v

CMD ["bash", "/code/run-docker.sh"]
