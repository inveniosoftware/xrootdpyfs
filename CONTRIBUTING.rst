Contributing
============

Bug reports, feature requests, and other contributions are welcome.
If you find a demonstrable problem that is caused by the code of this
library, please:

1. Search for `already reported problems
   <https://github.com/inveniosoftware/xrootdpyfs/issues>`_.
2. Check if the issue has been fixed or is still reproducible on the
   latest `master` branch.
3. Create an issue with **a test case**.

If you create a feature branch, you can run the tests to ensure everything is
operating correctly. The easiest is to run the tests using Docker:

.. code-block:: console

    $ docker build -t xrootd .
    $ docker run -h xrootdpyfs -it xrootd

You can also run the tests locally:

.. code-block:: console

    $ ./run-tests.sh

You will however need to start a local XRootD server, e.g.:

.. code-block:: console

    $ xrootd -b -l /dev/null /tmp <tmpfolder>

where, ``<tmpfolder>`` is dependent on your system (e.g. on OS X it is
``/var/folders``, while on Linux it can be left empty).

.. note::
   XRootD have issues with Docker's default hostname, thus it is important to
   supply a host name to ``docker run`` via the ``-h`` option.
