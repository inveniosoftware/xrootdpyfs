# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

r"""XRootDFS is a PyFilesystem interface for XRootD.

XRootD protocol aims at giving high performance, scalable fault tolerant access
to data repositories of many kinds. The XRootDFS adds a high-level interface
on top of the existing Python interface (pyxrootd) and makes it easy to e.g.
copy a directory in parallel or recursively remove a directory.

.. testsetup::

   from os.path import dirname, join, exists
   import os
   import shutil
   import tempfile

   if exists("/tmp/xrootdfs"):
       shutil.rmtree("/tmp/xrootdfs")
   os.makedirs("/tmp/xrootdfs")
   f = open("/tmp/xrootdfs/test.txt", "w")
   f.write("Welcome to xrootdfs!")
   f.close()

.. testcleanup::

   shutil.rmtree("/tmp/xrootdfs")

.. _install:

Installation
============

If you just want to try out the library, the easiest is to use Docker. See
:ref:`getting-started` below for details.

XRootDFS depends on `PyFilesystem <http://docs.pyfilesystem.org>`_ and
`XRootD Python bindings <http://xrootd.org/doc/python/xrootd-python-0.1.0/>`_.

XRootDFS is not Python 3 compatible due to the underlying Python bindings not
being Python 3 compatible.

XRootD Python bindings
----------------------
The XRootD Python bindings can be somewhat tricky to install if this is your
first experience with XRootD. First you must install XRootD as usual, then the
Python bindings. The Python bindings are installed using
``python setup.py install`` and requires access to the xrootd headers and
library. If these can't be found you need to set the ``XRD_LIBDIR`` and
``XRD_INCDIR`` environment variables. See the OS X example below.

Cent OS 7/YUM based
~~~~~~~~~~~~~~~~~~~

Install XRootD + Python bindings using the official YUM repositories, e.g.:

.. code-block:: console

   $ rpm -Uvh \
     http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
   $ yum install -y xrootd xrootd-server xrootd-client xrootd-client-devel \
     xrootd-python

See http://xrootd.org/dload.html to get the YUM repository addresses for other
RedHat based distributions/versions.

Ubuntu
~~~~~~

There is no official support for XRootD on Ubuntu, so you will have to install
XRootD from the source distribution.

OS X
~~~~

First, install XRootD using Homebrew:

.. code-block:: console

    $ brew install xrootd

Next, install the XRootD Python bindings:

.. code-block:: console

   $ xrootd -v
   v4.1.1
   $ VER=4.1.1
   $ git clone git://github.com/xrootd/xrootd-python.git
   $ cd xrootd-python
   $ XRD_LIBDIR=/usr/local/lib/ \
     XRD_INCDIR=/usr/local/Cellar/xrootd/$VER/include/xrootd \
     python setup.py install

Note, you might want to activate a virtualenv prior to running the last
``python setup.py install``. Also, in case you do not have ``cmake`` installed,
you can get it easily via ``brew install cmake``.

XRootDFS
--------
Once the XRootD Python bindings have been installed, xrootdfs itself is on PyPI
so all you need is:

.. code-block:: console

    $ pip install xrootdfs

.. _getting-started:

Getting started
===============

The easiest way to run the examples is to use the provided docker container.
This way you do not need to have a local XRootD server plus all the
libraries installed:

.. code-block:: console

   $ docker build -t xrootd .
   $ docker run -h xrootdfs -it xrootd bash

Next, start a XRootD server in the container and fire up an ipython shell:

.. code-block:: console

   [xrootdfs@xrootdfs code]$ xrootd -b -l /dev/null
   [xrootdfs@xrootdfs code]$ ipython

Quick examples
--------------

Here is a quick example of a file listing with the xrootd PyFilesystem
integration:

    >>> from xrootdfs import XRootDFS
    >>> fs = XRootDFS("root://localhost//tmp/")
    >>> fs.listdir("xrootdfs")
    ['test.txt']

Or, alternatively using the PyFilesystem opener (note the first
``import xrootdfs`` is required to ensure the XRootDFS opener is registered):

    >>> import xrootdfs
    >>> from fs.opener import opener
    >>> fs, path = opener.parse("root://localhost//tmp/")
    >>> fs.listdir("xrootdfs")
    [u'test.txt']

Reading files:

    >>> f = fs.open("xrootdfs/test.txt")
    >>> f.read()
    'Welcome to xrootdfs!'
    >>> f.close()

Reading files using the ``getcontents()`` method:

    >>> fs.getcontents("xrootdfs/test.txt")
    'Welcome to xrootdfs!'

Writing files:

    >>> f = fs.open("xrootdfs/hello.txt", "w+")
    >>> f.write("World")
    >>> f.close()

Writing files using the ``setcontents()`` method (returns the number of bytes
written):

    >>> fs.setcontents("xrootdfs/test.txt", "World")
    5
"""

from __future__ import absolute_import, print_function

from .fs import XRootDFS
from .opener import XRootDOpener
from .xrdfile import XRootDFile
from .version import __version__

__all__ = ('__version__', 'XRootDFS', 'XRootDOpener', 'XRootDFile')
