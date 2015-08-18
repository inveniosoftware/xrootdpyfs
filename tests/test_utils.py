# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""Test of XRootDFS."""

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from fs.errors import FSError

from xrootdfs.utils import spliturl


def test_spliturl():
    """Test spliturl."""
    root, path = spliturl("root://eosuser.cern.ch/eos/user/")
    assert root == "root://eosuser.cern.ch/"
    assert path == "/eos/user/"

    root, path = spliturl("root://eosuser.cern.ch/")
    assert root == "root://eosuser.cern.ch/"
    assert path == ""

    root, path = spliturl("root://eosuser.cern.ch//")
    assert root == "root://eosuser.cern.ch/"
    assert path == "//"

    root, path = spliturl("root://eosuser.cern.ch")
    assert root == "root://eosuser.cern.ch/"
    assert path == ""

    root, path = spliturl("root://user:pw@eosuser.cern.ch")
    assert root == "root://user:pw@eosuser.cern.ch/"
    assert path == ""

    root, path = spliturl("root://eosuser.cern.ch/?xrd.wantprot=krb5")
    assert root == "root://eosuser.cern.ch/?xrd.wantprot=krb5"
    assert path == ""

    root, path = spliturl("root://eosuser.cern.ch/eos?xrd.wantprot=krb5")
    assert root == "root://eosuser.cern.ch/?xrd.wantprot=krb5"
    assert path == "/eos"

    pytest.raises(FSError, spliturl, "http://localhost")
