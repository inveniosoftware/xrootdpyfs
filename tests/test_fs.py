# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""Test of XRootDFS."""

from __future__ import absolute_import, print_function, unicode_literals

import os
from os.path import exists, join

import pytest
from fixture import mkurl, tmppath
from fs.errors import BackReferenceError, DestinationExistsError, \
    DirectoryNotEmptyError, InvalidPathError, ResourceInvalidError
from xrootdfs import XRootDFile, XRootDFS
from xrootdfs.utils import spliturl


def test_init(tmppath):
    """Test initialization."""
    fs = XRootDFS("root://127.0.0.1//tmp/")
    assert fs.client
    assert fs.base_path == "//tmp/"
    assert fs.root_url == "root://127.0.0.1"

    XRootDFS("root://user:pw@eosuser.cern.ch//")
    XRootDFS("root://eosuser.cern.ch//")
    XRootDFS("root://eosuser.cern.ch//")
    pytest.raises(InvalidPathError, XRootDFS, "http://localhost")
    pytest.raises(InvalidPathError, XRootDFS, "root://eosuser.cern.ch//lhc//")

    rooturl = mkurl(tmppath)
    fs = XRootDFS(rooturl)
    root_url, base_path, qargs = spliturl(rooturl)
    assert fs.client
    assert fs.base_path == base_path
    assert fs.root_url == root_url
    assert fs.query is None

    qarg = "xrd.wantprot=krb5"
    fs = XRootDFS(rooturl + '?' + qarg)
    root_url, base_path, qargs = spliturl(rooturl + '?' + qarg)
    assert fs.base_path == base_path
    assert fs.root_url == root_url
    assert fs.query == qarg
    assert qargs == qarg


def test_p():
    """Test path combine."""
    fs = XRootDFS("root://eosuser.cern.ch//eos/user/")
    assert fs._p("./") == "//eos/user"
    assert fs._p("l") == "//eos/user/l"
    assert fs._p("/eos") == "//eos"
    assert fs._p("../") == "//eos"
    assert fs._p("../project/test") == "//eos/project/test"
    assert fs._p("../project/../test") == "//eos/test"
    pytest.raises(BackReferenceError, fs._p, "../../../test")


def test_listdir(tmppath):
    """Test listdir."""
    rooturl = mkurl(tmppath)

    dirs = XRootDFS(rooturl).listdir()
    assert len(dirs) == 1
    assert 'data' in dirs

    dirs = XRootDFS(rooturl).listdir("data")
    assert len(dirs) == 4

    dirs = XRootDFS(rooturl + "/data").listdir("afolder", full=True)
    assert 'afolder/afile.txt' in dirs

    dirs = XRootDFS(rooturl + "/data").listdir("afolder/../bfolder", full=True)
    assert 'bfolder/bfile.txt' in dirs

    dirs = XRootDFS(rooturl + "/data").listdir(
        "afolder", absolute=True)
    assert '/' + tmppath + "/data/afolder/afile.txt" in dirs

    # abosolute/full conflicts - full wins.
    dirs = XRootDFS(rooturl + "/data").listdir(
        "afolder", absolute=True, full=True)
    assert "afolder/afile.txt" in dirs

    dirs = XRootDFS(rooturl).listdir("data", wildcard="*.txt")
    assert 'testa.txt' in dirs
    assert 'afolder' not in dirs


def test_isfile(tmppath):
    """Test isfile."""
    rooturl = mkurl(tmppath)
    assert XRootDFS(rooturl).isfile("data/testa.txt")
    assert not XRootDFS(rooturl).isfile("data")
    pytest.raises(InvalidPathError, XRootDFS(rooturl).isfile, "nofile")


def test_isdir(tmppath):
    """Test isdir."""
    rooturl = mkurl(tmppath)
    assert not XRootDFS(rooturl).isdir("data/testa.txt")
    assert XRootDFS(rooturl).isdir("data")
    pytest.raises(InvalidPathError, XRootDFS(rooturl).isdir, "nofile")


def test_exists(tmppath):
    """Test exists."""
    rooturl = mkurl(tmppath)
    assert XRootDFS(rooturl).exists("data/testa.txt")
    assert XRootDFS(rooturl).exists("data")
    assert not XRootDFS(rooturl).exists("nofile")


def test_makedir(tmppath):
    """Test makedir."""
    rooturl = mkurl(tmppath)

    # Dir in parent
    assert not XRootDFS(rooturl).exists("somedir")
    assert XRootDFS(rooturl).makedir("somedir")
    assert XRootDFS(rooturl).exists("somedir")
    assert exists(join(tmppath, "somedir"))

    # if the path is already a directory, and allow_recreate is False
    print("DestinationExistsError")
    assert pytest.raises(DestinationExistsError, XRootDFS(rooturl).makedir,
                         "data")

    # allow_recreate
    assert XRootDFS(rooturl).makedir("data", allow_recreate=True)

    # if a containing directory is missing and recursive is False
    assert pytest.raises(ResourceInvalidError,
                         XRootDFS(rooturl).makedir, "aa/bb/cc")

    # Recursive
    assert not XRootDFS(rooturl).exists("aa/bb/cc")
    assert XRootDFS(rooturl).makedir("aa/bb/cc", recursive=True)
    assert XRootDFS(rooturl).exists("aa/bb/cc")

    # if a path is an existing file
    assert pytest.raises(DestinationExistsError, XRootDFS(rooturl).makedir,
                         "data/testa.txt")


def test_remove(tmppath):
    """Test remove."""
    rooturl = mkurl(tmppath)

    assert XRootDFS(rooturl).exists("data/testa.txt")
    XRootDFS(rooturl).remove("data/testa.txt")
    assert not XRootDFS(rooturl).exists("data/testa.txt")

    # Does not exists
    assert pytest.raises(ResourceInvalidError, XRootDFS(rooturl).remove,
                         "a/testa.txt")

    # Directory not empty
    assert pytest.raises(DirectoryNotEmptyError, XRootDFS(rooturl).remove,
                         "data")

    # Remove emptydir
    assert XRootDFS(rooturl).makedir("emptydir")
    assert XRootDFS(rooturl).remove("emptydir")


def test_open(tmppath):
    """Test fs.open()"""
    # Create a file to open.
    file_name = 'data/testa.txt'
    contents = 'testa.txt'
    xrd_rooturl = mkurl(tmppath)

    full_file_path = '/' + join(tmppath, file_name)

    # Open file w/ xrootd
    xrdfs = XRootDFS(xrd_rooturl)
    xfile = xrdfs.open(file_name, mode='r')
    assert xfile
    assert type(xfile) == XRootDFile

    # cleanup
    os.remove(full_file_path)
