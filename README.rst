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


Documentation
=============
Documentation is available at <http://pythonhosted.org/xrootdpyfs/> or can be
build using Sphinx::

    pip install Sphinx
    python setup.py build_sphinx

Testing
=======
Running the tests are most easily done using docker:

.. code-block:: console

    $ docker build -t xrootd . && docker run -h xrootdpyfs -it xrootd
