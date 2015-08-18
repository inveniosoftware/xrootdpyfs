Contributing
============

Bug reports, feature requests, and other contributions are welcome.
If you find a demonstrable problem that is caused by the code of this
library, please:

1. Search for `already reported problems
   <https://github.com/inveniosoftware/xrootdfs/issues>`_.
2. Check if the issue has been fixed or is still reproducible on the
   latest `master` branch.
3. Create an issue with **a test case**.

If you create a feature branch, you can run the tests to ensure everything is
operating correctly. The easiest is to run the tests using Docker:

.. code-block:: console

    $ docker build -t xrootd .
    $ docker run -h xrootdfs -it xrootd

You can also run the tests locally:

.. code-block:: console

    $ ./run-tests.sh

You will however need to start a local XRootD server, e.g.:

.. code-block:: console

    $ xrootd -b -l /dev/null <tmpfolder>

where, ``<tmpfolder>`` is dependent on your system (e.g. on OS X it is
``/var/folders``, while on Linux it can be left empty).

.. note::
   XRootD have issues with Docker's default hostname, thus it's import to
   supply a host name to ``docker run`` via the ``-h`` option.

Installing an XRootD server
---------------------------

Cent OS 7/YUM based
~~~~~~~~~~~~~~~~~~~

Install XRootD using the official YUM repositories, e.g.:

.. code-block:: console

   $ rpm -Uvh http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
   $ yum install -y xrootd xrootd-server xrootd-client xrootd-client-devel xrootd-python

See http://xrootd.org/dload.html to get the YUM repository addresses for other
RedHat based distributions/versions.

Ubuntu
~~~~~~

TODO

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
   $ XRD_LIBDIR=/usr/local/lib/ XRD_INCDIR=/usr/local/Cellar/xrootd/$VER/include/xrootd python setup.py install

Note, you might want to activate a virtualenv prior to running the last
``python setup.py install``. Also, in case you do not have ``cmake`` installed,
you can get it easily via ``brew install cmake``.
