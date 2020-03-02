# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""Test of XRootDPyFS utils."""

from __future__ import absolute_import, print_function

from XRootD.client.flags import OpenFlags
from xrootdpyfs.utils import is_valid_path, spliturl, \
    translate_file_mode_to_flags


def test_spliturl():
    """Test spliturl."""
    root, path, args = spliturl("root://eosuser.cern.ch//eos/user/")
    assert root == "root://eosuser.cern.ch"
    assert path == "//eos/user/"

    root, path, args = spliturl("root://eosuser.cern.ch//")
    assert root == "root://eosuser.cern.ch"
    assert path == "//"

    root, path, arg = spliturl("root://eosuser.cern.ch//eos?xrd.wantprot=krb5")
    assert root == "root://eosuser.cern.ch"
    assert path == "//eos"
    assert arg == "xrd.wantprot=krb5"

    root, path, arg = spliturl("root://localhost//")
    assert root == "root://localhost"
    assert path == "//"
    assert arg == ""


def test_is_valid_path():
    """Test is valid path."""
    assert is_valid_path("//")
    assert is_valid_path("//something/wicked/this/tub/comes/")
    assert is_valid_path("//every/time")
    assert not is_valid_path("")
    assert not is_valid_path("/")
    assert not is_valid_path("///")
    assert not is_valid_path("//missing//what")


def test_translate_file_mode_to_flags():
    """Test mode to xrootd flags translation."""
    assert translate_file_mode_to_flags('in') == 0
    assert translate_file_mode_to_flags('r') == OpenFlags.READ
    assert translate_file_mode_to_flags('r-') == OpenFlags.READ
    assert bool(translate_file_mode_to_flags('r+') & (
        OpenFlags.UPDATE | OpenFlags.READ))

    assert translate_file_mode_to_flags('a') == OpenFlags.UPDATE
    assert translate_file_mode_to_flags('a+') == OpenFlags.UPDATE

    assert translate_file_mode_to_flags('w') == OpenFlags.DELETE
    assert translate_file_mode_to_flags('w-') == OpenFlags.DELETE
    assert translate_file_mode_to_flags('w+') == OpenFlags.DELETE
