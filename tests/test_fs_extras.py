# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""Test of XRootDPyFS methods not implemented locally."""

from __future__ import absolute_import, print_function

import pytest
from conftest import mkurl
from fs.errors import ResourceNotFoundError
from xrootdpyfs import XRootDPyFS


def test_getcontents(tmppath):
    """Test getcontents."""
    fs = XRootDPyFS(mkurl(tmppath))
    assert fs.getcontents('data/testa.txt') == b"testa.txt\n"
    pytest.raises(ResourceNotFoundError, fs.getcontents, 'data/invalid.txt')


def test_setcontents(tmppath):
    """Test setcontents."""
    fs = XRootDPyFS(mkurl(tmppath))
    fs.setcontents('data/testa.txt', "mytest")
    assert fs.getcontents('data/testa.txt') == b"mytest"
