# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

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
