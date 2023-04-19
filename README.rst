============
 XRootDPyFS
============

.. image:: https://github.com/inveniosoftware/xrootdpyfs/actions?query=workflow%3ACI.svg?branch=master
    :target: https://github.com/inveniosoftware/xrootdpyfs/actions?query=workflow%3ACI
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

Build the image:

.. code-block:: console

   $ docker build --platform linux/amd64 -t xrootd .

Run the container and launch `xrootd`:

.. code-block:: console

   $ docker run --platform linux/amd64 -h xrootdpyfs -it xrootd bash

You will see the logs in the stdout. Next, in another shell, connect the container
and fire up an ipython shell:

.. code-block:: console

   $ docker ps  # find the container id
   $ docker exec -it <container-id> bash
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
    >>> from fs.opener import open_fs
    >>> fs = open_fs("root://localhost//tmp/")
    >>> fs.listdir("xrootdpyfs")
    ['test.txt']

Reading files:

    >>> f = fs.open("xrootdpyfs/test.txt")
    >>> f.read()
    b'Hello XRootD!\n'
    >>> f.close()

Reading files using the ``readtext()`` method:

    >>> fs.readtext("xrootdpyfs/test.txt")
    b'Hello XRootD!\n'

Writing files:

    >>> f = fs.open("xrootdpyfs/hello.txt", "w+")
    >>> f.write("World")
    >>> f.close()

Writing files using the ``writetext()`` method:

    >>> fs.writetext("xrootdpyfs/test.txt", "World")

Development
===========

The easiest way to develop is to build the Docker image and mount
the source code as a volume to test any code modification with a
running XRootD server:

.. code-block:: console

   $ docker build --platform linux/amd64 -t xrootd --progress=plain .
   $ docker run --platform linux/amd64 -h xrootdpyfs -it -v <absolute path to this project>:/code xrootd bash
   [xrootdpyfs@xrootdpyfs code]$ xrootd

In another shell:

.. code-block:: console

   $ docker ps  # find the container id
   $ docker exec -it <container-id> bash
   [xrootdpyfs@xrootdpyfs code]$ python -m pytest -vvv tests

If you want to test a specific version of xrootd, run:

.. code-block:: console

   $ docker build --platform linux/amd64 --build-arg xrootd_version=4.12.7 -t xrootd --progress=plain .

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

    $ docker build --platform linux/amd64 -t xrootd . && docker run --platform linux/amd64 -h xrootdpyfs -it xrootd
