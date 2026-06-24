# SPDX-FileCopyrightText: 2015-2023 CERN.
# SPDX-License-Identifier: BSD-3-Clause

"""Simple performance test of XRootD PyFilesystem-like wrapper.

Tests:

- Reading and writing a 100MB + 10KB file.
- Compares XRootD python binding vs PyFilesystem
- Local PyFileSystem vs XRootD PyFilesystem
"""

import cProfile
import os
import pstats
import shutil
import subprocess
import tempfile
import time
from io import StringIO
from os.path import join

from XRootD import client

from xrootdpyfs import XRootDPyFS


def teardown(tmppath):
    """Tear down performance test."""
    shutil.rmtree(tmppath)


def setup():
    """Setup test files for performance test."""
    filename = "testfile"
    tmppath = tempfile.mkdtemp()
    filepath = join(tmppath, filename)

    # Create test file with random data using subprocess
    count = 1024 * 10
    subprocess.check_call(
        ["dd", "bs=1024", f"count={count}", "if=/dev/urandom", f"of={filepath}"]
    )

    return filename, tmppath, filepath


#
# Test methods
#
def read_pyfs_chunks(url, filename, mode="rb", chunksize=2097152, n=100):
    """Read a file in chunks."""
    t1 = time.time()

    fs = XRootDPyFS(url)
    assert fs.exists(filename)
    i = 0
    while i < n:
        fsfile = fs.open(filename, mode="rb")
        while True:
            data = fsfile.read(chunksize)
            if not data:
                break
        i += 1

    t2 = time.time()
    return (t2 - t1) / n


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
    return (t2 - t1) / n


def profile_start():
    """Start profiling code."""
    pr = cProfile.Profile()
    pr.enable()
    return pr


def profile_end(pr):
    """Write profile output."""
    pr.disable()
    s = StringIO()
    sortby = "tottime"
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print(s.getvalue())


def main():
    """Main entry point."""
    filename, tmppath, testfilepath = setup()

    try:
        n = 10
        dirurl = "root://localhost/{0}".format(tmppath)
        rooturl = "root://localhost/{0}".format(testfilepath)

        print("osfs:", testfilepath, read_pyfs_chunks(dirurl, filename, n=n))
        print("pyxrootd:", rooturl, read_pyxrootd_chunks(rooturl, n=n))

        pr = profile_start()
        print(
            "xrootdpyfs:", rooturl, read_pyfs_chunks(dirurl, filename, mode="rb-", n=n)
        )
        profile_end(pr)
    finally:
        teardown(tmppath)


if __name__ == "__main__":
    main()
