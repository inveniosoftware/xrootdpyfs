# SPDX-FileCopyrightText: 2015 CERN.
# SPDX-License-Identifier: BSD-3-Clause

"""Test of XRootDPyFS methods not implemented locally."""

import pytest
from conftest import mkurl
from fs.errors import ResourceNotFound

from xrootdpyfs import XRootDPyFS


def test_readtext(tmppath):
    """Test readtext."""
    fs = XRootDPyFS(mkurl(tmppath))
    assert fs.readtext("data/testa.txt") == b"testa.txt\n"
    pytest.raises(ResourceNotFound, fs.readtext, "data/invalid.txt")


def test_writetext(tmppath):
    """Test writetext."""
    fs = XRootDPyFS(mkurl(tmppath))
    fs.writetext("data/testa.txt", "mytest")
    assert fs.readtext("data/testa.txt") == b"mytest"
