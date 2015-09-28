# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""Test of XRootDFS methods not implemented locally."""

from __future__ import absolute_import, print_function

import pytest
from fs.errors import ResourceNotFoundError

from conftest import mkurl
from xrootdfs import XRootDFS


def test_getcontents(tmppath):
    """Test getcontents."""
    fs = XRootDFS(mkurl(tmppath))
    assert fs.getcontents('data/testa.txt') == "testa.txt\n"
    pytest.raises(ResourceNotFoundError, fs.getcontents, 'data/invalid.txt')


def test_setcontents(tmppath):
    """Test setcontents."""
    fs = XRootDFS(mkurl(tmppath))
    fs.setcontents('data/testa.txt', "mytest")
    assert fs.getcontents('data/testa.txt') == "mytest"
