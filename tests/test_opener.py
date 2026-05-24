# SPDX-FileCopyrightText: 2015 CERN.
# SPDX-License-Identifier: BSD-3-Clause

"""Test of XRootDPyOpener."""

from conftest import mkurl
from fs.opener import open_fs


def test_open_fs_create(tmppath):
    """Test open with create."""
    rooturl = mkurl(tmppath)
    fs = open_fs(f"{rooturl}/non-existing")
    assert fs.listdir("./")
    assert not fs.exists("/non-existing")
    fs = open_fs(rooturl + "/non-existing", create=True)
    assert fs.exists("/non-existing")
