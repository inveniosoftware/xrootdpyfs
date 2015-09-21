==========
 XRootDFS
==========

.. image:: https://travis-ci.org/inveniosoftware/xrootdfs.svg?branch=master
    :target: https://travis-ci.org/inveniosoftware/xrootdfs
.. image:: https://coveralls.io/repos/inveniosoftware/xrootdfs/badge.svg?branch=master
    :target: https://coveralls.io/r/inveniosoftware/xrootdfs
.. image:: https://pypip.in/v/xrootdfs/badge.svg
   :target: https://crate.io/packages/xrootdfs/

XRootDFS is a PyFilesystem interface to XRootD.

Getting started
===============

If you just want to try out the library, the easiest is to use Docker.

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

Writing files using the ``setcontents()`` method:

    >>> fs.setcontents("xrootdfs/test.txt", "World")


Documentation
=============
Documentation is available at <http://pythonhosted.org/xrootdfs/> or can be
build using Sphinx::

    pip install Sphinx
    python setup.py build_sphinx

Testing
=======
Running the tests are most easily done using docker:

.. code-block:: console

    $ docker build -t xrootd . && docker run -h xrootdfs -it xrootd
