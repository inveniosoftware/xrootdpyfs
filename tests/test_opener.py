# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

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
