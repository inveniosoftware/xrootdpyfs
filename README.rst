==========
 XRootDFS
==========

.. image:: https://travis-ci.org/inveniosoftware/xrootdfs.svg?branch=master
    :target: https://travis-ci.org/inveniosoftware/xrootdfs
.. image:: https://coveralls.io/repos/inveniosoftware/xrootdfs/badge.svg?branch=master
    :target: https://coveralls.io/r/inveniosoftware/xrootdfs
.. image:: https://pypip.in/v/xrootdfs/badge.svg
   :target: https://crate.io/packages/xrootdfs/
.. image:: https://pypip.in/d/xrootdfs/badge.svg
   :target: https://crate.io/packages/xrootdfs/

XRootDFS is a PyFilesystem interface to XRootD.

Installation
============

The XRootDFS package is on PyPI so all you need is:

.. code-block:: console

    $ pip install XRootDFS

XRootDFS depends on `PyFilesystem <http://docs.pyfilesystem.org>`_ and
`XRootD Python bindings <http://xrootd.org/doc/python/xrootd-python-0.1.0/>`_.

Quick example
-------------

Here is a quick example of a file listing with the xrootd PyFilesystem
integration:

    >>> from xrootdfs import XRootDFS
    >>> fs = XRootDFS("root://localhost/tmp/")
    >>> fs.listdir("xrootdfs")
    ['test.txt']

Or, alternatively using the PyFilesystem opener:

    >>> import xrootdfs
    >>> from fs.opener import opener
    >>> fs, path = opener.parse("root://localhost/tmp/")
    >>> fs.listdir("xrootdfs")
    [u'test.txt']

Documentation
=============
Documentation is available at <http://xrootdfs.readthedocs.org> or can be build
using Sphinx::

    pip install Sphinx
    python setup.py build_sphinx

Testing
=======
Running the tests are most easily done using docker:

.. code-block:: console

    $ docker build -t xrootd .
    $ docker run -h xrootdfs -it xrootd
