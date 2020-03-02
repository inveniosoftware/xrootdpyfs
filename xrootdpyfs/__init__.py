# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015-2020 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

r"""XRootDPyFS is a PyFilesystem interface for XRootD.

XRootD protocol aims at giving high performance, scalable fault tolerant access
to data repositories of many kinds. The XRootDPyFS adds a high-level interface
on top of the existing Python interface (pyxrootd) and makes it easy to e.g.
copy a directory in parallel or recursively remove a directory.

.. testsetup::

   from os.path import dirname, join, exists
   import os
   import shutil
   import tempfile

   if exists("/tmp/xrootdpyfs"):
       shutil.rmtree("/tmp/xrootdpyfs")
   os.makedirs("/tmp/xrootdpyfs")
   f = open("/tmp/xrootdpyfs/test.txt", "w")
   f.write("Welcome to xrootdpyfs!")
   f.close()

.. testcleanup::

   shutil.rmtree("/tmp/xrootdpyfs")

.. _install:

Installation
============

If you just want to try out the library, the easiest is to use Docker. See
:ref:`getting-started` below for details.

XRootDPyFS depends on `PyFilesystem <http://docs.pyfilesystem.org>`_ and
`XRootD Python bindings <http://xrootd.org/doc/python/xrootd-python-0.1.0/>`_.

XRootDPyFS is not Python 3 compatible due to the underlying Python bindings not
being Python 3 compatible.

XRootD Python bindings
----------------------
In general, to install the XRootD Python bindings you will just
``pip install xrootd``: this will download, compile and install the module.
The required dependencies that have to be already pre-installed in your system
are development tools such as compiler and OpenSSL libs.
Unfortunately there is no clear documentation at the moment of what is exactly
needed. You could check the `spec
<https://github.com/xrootd/xrootd/blob/master/packaging/rhel/xrootd.spec.in>`_
file if it can be of any help.

To test the Python bindings, you can setup xrootd server in your machine.
See the OS X example below.

Cent OS 7/YUM based
~~~~~~~~~~~~~~~~~~~

Install XRootD + Python bindings using the official YUM repositories, e.g.:

.. code-block:: console

   $ rpm -Uvh \
     https://xrootd.slac.stanford.edu/binaries/xrootd-stable-slc7.repo
   $ yum install -y xrootd

See https://xrootd.slac.stanford.edu/dload.html to get the YUM repository
addresses for other RedHat based distributions/versions.

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

XRootDPyFS
----------
Once the XRootD Python bindings have been installed, xrootdpyfs itself is on
PyPI so all you need is:

.. code-block:: console

    $ pip install xrootdpyfs

.. _getting-started:

Getting started
===============

The easiest way to run the examples is to use the provided docker container.
This way you do not need to have a local XRootD server plus all the
libraries installed:

.. code-block:: console

   $ docker build -t xrootd .
   $ docker run -h xrootdpyfs -it xrootd bash

Next, start a XRootD server in the container and fire up an ipython shell:

.. code-block:: console

   [xrootdpyfs@xrootdpyfs code]$ xrootd -b -l /dev/null
   [xrootdpyfs@xrootdpyfs code]$ ipython

Quick examples
--------------

Here is a quick example of a file listing with the xrootd PyFilesystem
integration:

    >>> from xrootdpyfs import XRootDPyFS
    >>> fs = XRootDPyFS("root://localhost//tmp/")
    >>> fs.listdir("xrootdpyfs")
    ['test.txt']

Or, alternatively using the PyFilesystem opener (note the first
``import xrootdpyfs`` is required to ensure the XRootDPyFS
opener is registered):

    >>> import xrootdpyfs
    >>> from fs.opener import opener
    >>> fs, path = opener.parse("root://localhost//tmp/")
    >>> fs.listdir("xrootdpyfs")
    [u'test.txt']

Reading files:

    >>> f = fs.open("xrootdpyfs/test.txt")
    >>> f.read()
    'Welcome to xrootdpyfs!'
    >>> f.close()

Reading files using the ``getcontents()`` method:

    >>> fs.getcontents("xrootdpyfs/test.txt")
    'Welcome to xrootdpyfs!'

Writing files:

    >>> f = fs.open("xrootdpyfs/hello.txt", "w+")
    >>> f.write("World")
    >>> f.close()

Writing files using the ``setcontents()`` method (returns the number of bytes
written):

    >>> fs.setcontents("xrootdpyfs/test.txt", "World")
    5
"""

from __future__ import absolute_import, print_function

from .fs import XRootDPyFS
from .opener import XRootDPyOpener
from .version import __version__
from .xrdfile import XRootDPyFile

__all__ = ('__version__', 'XRootDPyFS', 'XRootDPyOpener', 'XRootDPyFile')
