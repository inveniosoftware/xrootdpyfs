# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""Test of XRootDOpener."""

from __future__ import absolute_import, print_function

from fs.opener import opener

from conftest import mkurl
from xrootdfs.opener import XRootDOpener  # no-qa


def test_parse(tmppath):
    """Test parse."""
    rooturl = mkurl(tmppath)
    fs, path = opener.parse(rooturl + "/data")
    assert path == "data"
    assert fs
    fs, path = opener.parse(rooturl + "/data/")
    assert path == ""
    assert fs


def test_parse_create(tmppath):
    """Test opendir."""
    rooturl = mkurl(tmppath)
    fs, path = opener.parse(rooturl + "/non-existing")
    assert not fs.exists(path)
    fs, path = opener.parse(rooturl + "/non-existing", create_dir=True)
    assert fs.exists(path)


def test_opendir(tmppath):
    """Test opendir."""
    rooturl = mkurl(tmppath)
    fs = opener.opendir(rooturl + "/data")
    assert fs.listdir()


def test_open():
    """."""
    # fsfile = opener.open('root://localhost/foo/bar/README')
