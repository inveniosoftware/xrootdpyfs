# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""Simple performance test of XRootD PyFilesystem wrapper.

Tests:

- Reading and writing a 100MB + 10KB file.
- Compares XRootD python binding vs PyFilesystem
- Local PyFileSystem vs XRootD PyFilesystem
"""

import cProfile
import os
import pstats
import shutil
import StringIO
import tempfile
import time
from os.path import join

from fs.opener import opener
from XRootD import client

from xrootdfs import XRootDOpener  # no-qa


def teardown(tmppath):
    """Tear down performance test."""
    shutil.rmtree(tmppath)


def setup():
    """Setup test files for performance test."""
    tmppath = tempfile.mkdtemp()
    filepath = join(tmppath, "testfile")

    # Create test file with random data
    os.system("dd bs=1024 count={1} </dev/urandom >{0}".format(
        filepath, 1024*10))

    return tmppath, filepath


#
# Test methods
#
def read_pyfs_chunks(url, chunksize=2097152, n=100):
    """Read a file in chunks."""
    t1 = time.time()

    i = 0
    while i < n:
        fsfile = opener.open(url, 'rb-')
        while True:
            data = fsfile.read(chunksize)
            if not data:
                break
        i += 1

    t2 = time.time()
    return (t2-t1)/n


def read_pyxrootd_chunks(url, chunksize=2097152, n=100):
    """Read a file in chunks."""
    t1 = time.time()

    i = 0
    while i < n:
        fsfile = client.File()
        fsfile.open(url)

        for chunk in fsfile.readchunks(offset=0, chunksize=chunksize):
            pass

        fsfile.close()
        i += 1

    t2 = time.time()
    return (t2-t1)/n


def profile_start():
    """Start profiling code."""
    pr = cProfile.Profile()
    pr.enable()
    return pr


def profile_end(pr):
    """Write profile output."""
    pr.disable()
    s = StringIO.StringIO()
    sortby = 'tottime'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print s.getvalue()


def main():
    """Main entry point."""
    tmppath, testfilepath = setup()

    try:
        n = 10
        rooturl = 'root://localhost/{0}'.format(testfilepath)
        osurl = testfilepath

        print("osfs:", osurl, read_pyfs_chunks(osurl, n=n))
        print("pyxrootd:", rooturl, read_pyxrootd_chunks(rooturl, n=n))

        pr = profile_start()
        print("xrootdfs:", rooturl, read_pyfs_chunks(rooturl, n=n))
        profile_end(pr)
    finally:
        teardown(tmppath)

if __name__ == "__main__":
    main()
