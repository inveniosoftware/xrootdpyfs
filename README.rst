============
 XRootDPyFS
============

.. image:: https://travis-ci.org/inveniosoftware/xrootdpyfs.svg?branch=master
    :target: https://travis-ci.org/inveniosoftware/xrootdpyfs
.. image:: https://coveralls.io/repos/inveniosoftware/xrootdpyfs/badge.svg?branch=master
    :target: https://coveralls.io/r/inveniosoftware/xrootdpyfs
.. image:: https://pypip.in/v/xrootdpyfs/badge.svg
   :target: https://crate.io/packages/xrootdpyfs/


XRootDPyFS is a PyFilesystem interface to XRootD.

XRootD protocol aims at giving high performance, scalable fault tolerant access
to data repositories of many kinds. The XRootDPyFS adds a high-level interface
on top of the existing Python interface (pyxrootd) and makes it easy to e.g.
copy a directory in parallel or recursively remove a directory.

Further documentation is available on https://xrootdpyfs.readthedocs.io/.

Getting started
===============

If you just want to try out the library, the easiest is to use Docker.

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
``import xrootdpyfs`` is required to ensure the XRootDPyFS opener is registered):

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

Writing files using the ``setcontents()`` method:

    >>> fs.setcontents("xrootdpyfs/test.txt", "World")

Development
===========

The easiest way to develop is to build the Docker image and mount
the source code as a volume to test any code modification with a
running XRootD server:

.. code-block:: console

   $ docker build -t xrootd .
   $ docker run -h xrootdpyfs -it -v <absolute path to this project>:/code xrootd bash
   [xrootdpyfs@xrootdpyfs code]$ xrootd -b -l /dev/null

If you want to test a specific version of xrootd, run:

.. code-block:: console

   $ docker build --build-arg xrootd_version=4.8.5 -t xrootd .

Documentation
=============
Documentation is available at <http://xrootdpyfs.readthedocs.io/> or can be
build using Sphinx::

    pip install Sphinx
    python setup.py build_sphinx

Testing
=======
Running the tests are most easily done using docker:

.. code-block:: console

    $ docker build -t xrootd . && docker run -h xrootdpyfs -it xrootd
