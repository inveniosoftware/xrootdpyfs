# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""Test of XRootDPyFS."""

import os
import types
from datetime import datetime
from functools import wraps
from os.path import exists, join

import pytest
from conftest import mkurl
from fs import ResourceType
from fs.errors import (
    DestinationExists,
    DirectoryNotEmpty,
    FSError,
    IllegalBackReference,
    InvalidPath,
    RemoteConnectionError,
    ResourceError,
    ResourceInvalid,
    ResourceNotFound,
    Unsupported,
)
from mock import Mock
from XRootD.client.responses import XRootDStatus

from xrootdpyfs import XRootDPyFile, XRootDPyFS
from xrootdpyfs.utils import spliturl


def test_init(tmppath):
    """Test initialization."""
    fs = XRootDPyFS("root://127.0.0.1//tmp/")
    assert fs.xrd_client
    assert fs.base_path == "//tmp/"
    assert fs.root_url == "root://127.0.0.1"

    XRootDPyFS("root://user:pw@eosuser.cern.ch//")
    XRootDPyFS("root://eosuser.cern.ch//")
    XRootDPyFS("root://eosuser.cern.ch//")
    pytest.raises(InvalidPath, XRootDPyFS, "http://localhost")
    pytest.raises(InvalidPath, XRootDPyFS, "root://eosuser.cern.ch//lhc//")

    rooturl = mkurl(tmppath)
    fs = XRootDPyFS(rooturl)
    root_url, base_path, qargs = spliturl(rooturl)
    assert fs.xrd_client
    assert fs.base_path == base_path
    assert fs.root_url == root_url
    assert fs.queryargs is None

    qarg = "xrd.wantprot=krb5"
    fs = XRootDPyFS(rooturl + "?" + qarg)
    root_url, base_path, qargs = spliturl(rooturl + "?" + qarg)
    assert fs.base_path == base_path
    assert fs.root_url == root_url
    assert fs.queryargs == {"xrd.wantprot": "krb5"}
    assert qargs == qarg

    qarg = "xrd.wantprot=krb5"
    fs = XRootDPyFS(rooturl + "?" + qarg, query={"xrd.k5ccname": "/tmp/krb"})

    assert fs.queryargs == {
        "xrd.wantprot": "krb5",
        "xrd.k5ccname": "/tmp/krb",
    }

    pytest.raises(
        KeyError, XRootDPyFS, rooturl + "?" + qarg, query={"xrd.wantprot": "krb5"}
    )


def test_p():
    """Test path combine."""
    fs = XRootDPyFS("root://eosuser.cern.ch//eos/user/")
    assert fs._p("./") == "//eos/user"
    assert fs._p("l") == "//eos/user/l"
    assert fs._p("/eos/user") == "//eos/user"
    assert fs._p("//eos/user") == "//eos/user"
    assert fs._p("/eos/user/folder") == "//eos/user/folder"
    assert fs._p("//eos/user/folder") == "//eos/user/folder"
    assert fs._p("../") == "//eos"
    assert fs._p("../project/test") == "//eos/project/test"
    assert fs._p("../project/../test") == "//eos/test"
    pytest.raises(IllegalBackReference, fs._p, "../../../test")


def test_query_error(tmppath):
    """Test unknown error from query."""
    fs = XRootDPyFS(mkurl(tmppath))
    fake_status = {
        "status": 3,
        "code": 101,
        "ok": False,
        "errno": 0,
        "error": True,
        "message": "[FATAL] Invalid address",
        "fatal": True,
        "shellcode": 51,
    }
    fs.xrd_client.query = Mock(return_value=(XRootDStatus(fake_status), None))
    pytest.raises(FSError, fs._query, 3, "data/testa.txt")


def test_ilistdir(tmppath):
    """Test the ilistdir returns a generator."""
    rooturl = mkurl(tmppath)
    assert isinstance(XRootDPyFS(rooturl).ilistdir(), types.GeneratorType)


def test_listdir(tmppath):
    """Test listdir."""
    rooturl = mkurl(tmppath)

    dirs = XRootDPyFS(rooturl).listdir()
    assert len(dirs) == 1
    assert "data" in dirs

    dirs = XRootDPyFS(rooturl).listdir("data")
    assert len(dirs) == 5

    dirs = XRootDPyFS(rooturl + "/data").listdir("afolder", full=True)
    assert "afolder/afile.txt" in dirs

    dirs = XRootDPyFS(rooturl + "/data").listdir("afolder/../bfolder", full=True)
    assert "bfolder/bfile.txt" in dirs

    dirs = XRootDPyFS(rooturl + "/data").listdir("afolder", absolute=True)
    assert "/" + tmppath + "/data/afolder/afile.txt" in dirs

    # absolute/full conflicts - full wins.
    dirs = XRootDPyFS(rooturl + "/data").listdir("afolder", absolute=True, full=True)
    assert "afolder/afile.txt" in dirs

    dirs = XRootDPyFS(rooturl).listdir("data", wildcard="*.txt")
    assert "testa.txt" in dirs
    assert "afolder" not in dirs

    pytest.raises(
        ValueError, XRootDPyFS(rooturl).listdir, "data", files_only=True, dirs_only=True
    )

    pytest.raises(ResourceNotFound, XRootDPyFS(rooturl).listdir, "invalid")


def test_isfile(tmppath):
    """Test isfile."""
    rooturl = mkurl(tmppath)
    assert XRootDPyFS(rooturl).isfile("data/testa.txt")
    assert not XRootDPyFS(rooturl).isfile("data")
    assert not XRootDPyFS(rooturl).isfile("nofile")


def test_isdir(tmppath):
    """Test isdir."""
    rooturl = mkurl(tmppath)
    assert not XRootDPyFS(rooturl).isdir("data/testa.txt")
    assert XRootDPyFS(rooturl).isdir("data")
    assert not XRootDPyFS(rooturl).isdir("nofile")


def test_exists(tmppath):
    """Test exists."""
    rooturl = mkurl(tmppath)
    assert XRootDPyFS(rooturl).exists("data/testa.txt")
    assert XRootDPyFS(rooturl).exists("data")
    assert not XRootDPyFS(rooturl).exists("nofile")


def test_makedir(tmppath):
    """Test makedir."""
    rooturl = mkurl(tmppath)

    # Dir in parent
    assert not XRootDPyFS(rooturl).exists("somedir")
    assert XRootDPyFS(rooturl).makedir("somedir")
    assert XRootDPyFS(rooturl).exists("somedir")
    assert exists(join(tmppath, "somedir"))

    # if the path is already a directory, and allow_recreate is False
    assert pytest.raises(DestinationExists, XRootDPyFS(rooturl).makedir, "data")

    # allow_recreate
    assert XRootDPyFS(rooturl).makedir("data", allow_recreate=True)

    # if a containing directory is missing and recursive is False
    assert pytest.raises(ResourceNotFound, XRootDPyFS(rooturl).makedir, "aa/bb/cc")

    # Recursive
    assert not XRootDPyFS(rooturl).exists("aa/bb/cc")
    assert XRootDPyFS(rooturl).makedir("aa/bb/cc", recursive=True)
    assert XRootDPyFS(rooturl).exists("aa/bb/cc")

    # if a path is an existing file
    assert pytest.raises(
        DestinationExists, XRootDPyFS(rooturl).makedir, "data/testa.txt"
    )


def test_unicode_paths(tmppath):
    """Test creation of unicode paths."""
    fs = XRootDPyFS(mkurl(tmppath))
    d = "\xe6\xf8\xe5"
    assert not fs.exists(d)
    assert fs.makedir(d)
    assert fs.exists(d)
    d = "\xc3\xb8\xc3\xa5\xc3\xa6"
    assert not fs.exists(d)
    assert fs.makedir(d)
    assert fs.exists(d)


def test_remove(tmppath):
    """Test remove."""
    rooturl = mkurl(tmppath)

    assert XRootDPyFS(rooturl).exists("data/testa.txt")
    XRootDPyFS(rooturl).remove("data/testa.txt")
    assert not XRootDPyFS(rooturl).exists("data/testa.txt")

    # Does not exists
    assert pytest.raises(ResourceNotFound, XRootDPyFS(rooturl).remove, "a/testa.txt")

    # Directory not empty
    assert pytest.raises(DirectoryNotEmpty, XRootDPyFS(rooturl).remove, "data")

    # Remove emptydir
    assert XRootDPyFS(rooturl).makedir("emptydir")
    assert XRootDPyFS(rooturl).remove("emptydir")


def test_remove_dir(tmppath):
    """Test removedir."""
    fs = XRootDPyFS(mkurl(tmppath))

    # Remove non-empty directory
    pytest.raises(DirectoryNotEmpty, fs.removedir, "data/bfolder/")

    # Use of recursive parameter
    pytest.raises(Unsupported, fs.removedir, "data/bfolder/", recursive=True)

    # Remove file
    pytest.raises(ResourceInvalid, fs.removedir, "data/testa.txt")

    # Remove empty directory
    fs.makedir("data/tmp")
    assert fs.removedir("data/tmp") and not fs.exists("data/tmp")

    # Remove non-empty directory
    assert fs.removedir("data/bfolder/", force=True)
    assert fs.removedir("data/", force=True)


def test_remove_dir_mock1(tmppath):
    """Test removedir."""
    fs = XRootDPyFS(mkurl(tmppath))

    status = XRootDStatus(
        {
            "status": 3,
            "code": 101,
            "ok": False,
            "errno": 0,
            "error": True,
            "message": "[FATAL] Invalid address",
            "fatal": True,
            "shellcode": 51,
        }
    )
    fs.xrd_client.rm = Mock(return_value=(status, None))
    pytest.raises(ResourceError, fs.removedir, "data/bfolder/", force=True)


def test_remove_dir_mock2(tmppath):
    """Test removedir."""
    fs = XRootDPyFS(mkurl(tmppath))

    status = XRootDStatus(
        {
            "status": 3,
            "code": 101,
            "ok": False,
            "errno": 0,
            "error": True,
            "message": "[FATAL] Invalid address",
            "fatal": True,
            "shellcode": 51,
        }
    )

    def fail(f, fail_on):
        @wraps(f)
        def inner(path, **kwargs):
            if path == fail_on:
                return (status, None)
            return f(path, **kwargs)

        return inner

    fs.xrd_client.rmdir = fail(fs.xrd_client.rmdir, fs._p("data/bfolder/"))
    pytest.raises(ResourceError, fs.removedir, "data/", force=True)


def test_open(tmppath):
    """Test fs.open()"""
    # Create a file to open.
    file_name = "data/testa.txt"
    expected_content = b"testa.txt\n"
    xrd_rooturl = mkurl(tmppath)

    # Open file w/ xrootd
    xrdfs = XRootDPyFS(xrd_rooturl)
    xfile = xrdfs.open(file_name, mode="r")
    assert xfile
    assert xfile.path.endswith("data/testa.txt")
    assert type(xfile) == XRootDPyFile
    assert xfile.read() == expected_content
    xfile.close()

    # Test passing of querystring.
    xrdfs = XRootDPyFS(xrd_rooturl + "?xrd.wantprot=krb5")
    xfile = xrdfs.open(file_name, mode="r")
    assert xfile
    assert xfile.path.endswith("data/testa.txt?xrd.wantprot=krb5")
    assert type(xfile) == XRootDPyFile
    assert xfile.read() == expected_content
    xfile.close()


def _get_content(fs, path):
    f = fs.open(path, "r")
    content = f.read()
    f.close()
    return content


def test_rename(tmppath):
    """Test rename."""
    fs = XRootDPyFS(mkurl(tmppath))

    pytest.raises(DestinationExists, fs.rename, "data/testa.txt", "multiline.txt")
    pytest.raises(DestinationExists, fs.rename, "data/testa.txt", "afolder/afile.txt")
    pytest.raises(DestinationExists, fs.rename, "data/afolder", "bfolder")
    pytest.raises(DestinationExists, fs.rename, "data/afolder", "bfolder/bfile.txt")

    pytest.raises(ResourceNotFound, fs.rename, "data/invalid.txt", "afolder/afile.txt")

    assert fs.exists("data/testa.txt") and not fs.exists("data/testb.txt")
    fs.rename("data/testa.txt", "testb.txt")
    assert fs.exists("data/testb.txt") and not fs.exists("data/testa.txt")

    assert fs.exists("data/afolder/") and not fs.exists("data/cfolder/")
    fs.rename("data/afolder/", "cfolder")
    assert fs.exists("data/cfolder") and not fs.exists("data/afolder")

    fs.rename("data/cfolder/", "a/b/c/test")
    assert fs.exists("data/a/b/c/test/")


def test_getinfo(tmppath):
    """Test getinfo."""
    fs = XRootDPyFS(mkurl(tmppath))

    namespaces = ["details", "stat", "lstat", "link", "access", "xrootd"]

    # Info for file
    f = "data/testa.txt"
    info = fs.getinfo(f, namespaces)
    assert info.name == "testa.txt"
    assert info.is_dir is False
    assert info.size == os.stat(join(tmppath, f)).st_size
    assert info.type == ResourceType.file
    assert info.uid == b"*"
    assert info.gid == b"*"
    assert info.get("xrootd", "offline") is False
    assert info.get("xrootd", "writable") is True
    assert info.get("xrootd", "readable") is True
    assert info.get("xrootd", "executable") is False
    assert isinstance(info.created, datetime)
    assert isinstance(info.modified, datetime)
    assert isinstance(info.accessed, datetime)

    # Info for directory
    f = "data/"
    info = fs.getinfo(f, namespaces)
    assert info.name == ""
    assert info.is_dir is True
    assert info.size == os.stat(join(tmppath, f)).st_size
    assert info.type == ResourceType.directory
    assert info.uid == b"*"
    assert info.gid == b"*"
    assert info.get("xrootd", "offline") is False
    assert info.get("xrootd", "writable") is True
    assert info.get("xrootd", "readable") is True
    assert info.get("xrootd", "executable") is True
    assert isinstance(info.created, datetime)
    assert isinstance(info.modified, datetime)
    assert isinstance(info.accessed, datetime)

    # Non existing path
    pytest.raises(ResourceNotFound, fs.getinfo, "invalidpath/")


def test_getpathurl(tmppath):
    """Test getpathurl."""
    fs = XRootDPyFS(mkurl(tmppath))
    assert fs.getpathurl("data/testa.txt") == "root://localhost/{0}/{1}".format(
        tmppath, "data/testa.txt"
    )

    fs = XRootDPyFS(mkurl(tmppath), query={"xrd.wantprot": "krb5"})

    assert fs.getpathurl("data/testa.txt") == "root://localhost/{0}/{1}".format(
        tmppath, "data/testa.txt"
    )

    assert fs.getpathurl(
        "data/testa.txt", with_querystring=True
    ) == "root://localhost/{0}/{1}?xrd.wantprot=krb5".format(tmppath, "data/testa.txt")


def test_ping(tmppath):
    """Test ping method."""
    fs = XRootDPyFS(mkurl(tmppath))
    assert fs.xrd_ping()
    fake_status = {
        "status": 3,
        "code": 101,
        "ok": False,
        "errno": 0,
        "error": True,
        "message": "[FATAL] Invalid address",
        "fatal": True,
        "shellcode": 51,
    }
    fs.xrd_client.ping = Mock(return_value=(XRootDStatus(fake_status), None))
    pytest.raises(RemoteConnectionError, fs.xrd_ping)


def test_checksum(tmppath):
    """Test checksum method."""
    fs = XRootDPyFS(mkurl(tmppath))

    # Local xrootd server does not support checksum operation
    pytest.raises(Unsupported, fs.xrd_checksum, "data/testa.txt")

    # Let's fake a success response
    fake_status = {
        "status": 0,
        "code": 0,
        "ok": True,
        "errno": 0,
        "error": False,
        "message": "[SUCCESS] ",
        "fatal": False,
        "shellcode": 0,
    }
    fs.xrd_client.query = Mock(
        return_value=(XRootDStatus(fake_status), b"adler32 3836a69a\x00")
    )
    algo, val = fs.xrd_checksum("data/testa.txt")
    assert algo == "adler32" and val == "3836a69a"

    # Fake a bad response (e.g. on directory)
    fake_status = {
        "status": 1,
        "code": 400,
        "ok": False,
        "errno": 3011,
        "error": True,
        "message": "[ERROR] Server responded with an error: [3011] no such "
        "file or directory\n",
        "fatal": False,
        "shellcode": 54,
    }
    fs.xrd_client.query = Mock(return_value=(XRootDStatus(fake_status), None))
    pytest.raises(FSError, fs.xrd_checksum, "data/")


def test_move_good(tmppath):
    """Test move file."""
    fs = XRootDPyFS(mkurl(tmppath))

    src_exists = "data/testa.txt"
    dst_exists = "data/multiline.txt"
    dst_new = "data/ok.txt"
    dst_folder_exists = "data/bfolder/"
    dst_folder_new = "data/anothernewfolder/"
    content = _get_content(fs, src_exists)

    assert fs.exists(dst_exists)
    assert not fs.exists(dst_new)
    assert fs.exists(dst_folder_exists)
    assert not fs.exists(dst_folder_new)

    fs.move(src_exists, dst_new)
    assert not fs.exists(src_exists) and fs.exists(dst_new)

    fs.move(dst_new, src_exists)
    fs.move(src_exists, dst_folder_new)
    assert not fs.exists(src_exists) and fs.exists(dst_folder_new)

    fs.move(dst_folder_new, src_exists)
    fs.move(src_exists, dst_exists, overwrite=True)
    assert not fs.exists(src_exists) and fs.exists(dst_exists)
    assert content == _get_content(fs, dst_exists)

    fs.move(dst_exists, src_exists)
    fs.move(src_exists, dst_folder_exists, overwrite=True)
    assert not fs.exists(src_exists) and fs.exists(dst_folder_exists)
    assert content == _get_content(fs, dst_folder_exists)


def test_movedir_good(tmppath):
    """Test move file."""
    fs = XRootDPyFS(mkurl(tmppath))

    src_exists = "data/afolder/"
    dst_exists = "data/multiline.txt"
    dst_new = "data/ok.txt"
    dst_folder_exists = "data/bfolder/"
    dst_folder_new = "data/anothernewfolder/"

    assert fs.isdir(src_exists)
    assert fs.exists(dst_exists)
    assert not fs.exists(dst_new)
    assert fs.exists(dst_folder_exists)
    assert not fs.exists(dst_folder_new)

    # Move to new folder (without trailing slash).
    fs.movedir(src_exists, dst_new)
    assert not fs.exists(src_exists) and fs.exists(dst_new)

    fs.movedir(dst_new, src_exists)  # reset
    # Move to new folder (with trailing slash).
    fs.movedir(src_exists, dst_folder_new)
    assert not fs.exists(src_exists) and fs.exists(dst_folder_new)

    fs.movedir(dst_folder_new, src_exists)  # reset
    # Move to existing filer with overwrite (i.e. will remove destination)
    fs.movedir(src_exists, dst_exists, overwrite=True)
    assert not fs.exists(src_exists) and fs.exists(dst_exists)
    assert fs.isdir(dst_exists)

    fs.movedir(dst_exists, src_exists)  # reset
    # Move to existing folder with overwrite (i.e. will remove destination)
    fs.movedir(src_exists, dst_folder_exists, overwrite=True)
    assert not fs.exists(src_exists) and fs.exists(dst_folder_exists)
    assert fs.isdir(dst_folder_exists)


def test_move_bad(tmppath):
    """Test move file."""
    fs = XRootDPyFS(mkurl(tmppath))

    src_exists = "data/testa.txt"
    src_new = "data/testb.txt"
    src_folder_exists = "data/afolder/"
    dst_exists = "data/multiline.txt"
    dst_new = "data/ok.txt"
    dst_folder_exists = "data/bfolder/"
    dst_folder_new = "data/anothernewfolder/"

    # Destination exists
    pytest.raises(DestinationExists, fs.move, src_exists, dst_exists)
    pytest.raises(DestinationExists, fs.move, src_exists, src_exists)
    pytest.raises(DestinationExists, fs.move, src_exists, dst_folder_exists)

    # Cannot move dir
    pytest.raises(ResourceInvalid, fs.move, src_folder_exists, dst_new)
    pytest.raises(ResourceInvalid, fs.move, src_folder_exists, dst_folder_new)

    # Source doesn't exists
    pytest.raises(ResourceNotFound, fs.move, src_new, dst_exists)
    pytest.raises(ResourceNotFound, fs.move, src_new, dst_new)
    pytest.raises(ResourceNotFound, fs.move, src_new, dst_folder_exists)
    pytest.raises(ResourceNotFound, fs.move, src_new, dst_folder_new)


def test_movedir_bad(tmppath):
    """Test move file."""
    fs = XRootDPyFS(mkurl(tmppath))

    src_exists = "data/testa.txt"
    src_new = "data/testb.txt"
    src_folder_exists = "data/afolder/"
    src_folder_new = "data/newfolder/"
    dst_exists = "data/multiline.txt"
    dst_new = "data/ok.txt"
    dst_folder_exists = "data/bfolder/"
    dst_folder_new = "data/anothernewfolder/"

    # Destination exists
    pytest.raises(DestinationExists, fs.movedir, src_folder_exists, dst_exists)
    pytest.raises(DestinationExists, fs.movedir, src_folder_exists, dst_folder_exists)

    # Cannot move file
    pytest.raises(ResourceInvalid, fs.movedir, src_exists, dst_new)
    pytest.raises(ResourceInvalid, fs.movedir, src_exists, dst_folder_new)

    # Source doesn't exists
    pytest.raises(ResourceNotFound, fs.movedir, src_new, dst_exists)
    pytest.raises(ResourceNotFound, fs.movedir, src_new, dst_new)
    pytest.raises(ResourceNotFound, fs.movedir, src_new, dst_folder_exists)
    pytest.raises(ResourceNotFound, fs.movedir, src_new, dst_folder_new)

    pytest.raises(ResourceNotFound, fs.movedir, src_folder_new, dst_exists)
    pytest.raises(ResourceNotFound, fs.movedir, src_folder_new, dst_new)
    pytest.raises(ResourceNotFound, fs.movedir, src_folder_new, dst_folder_exists)
    pytest.raises(ResourceNotFound, fs.movedir, src_folder_new, dst_folder_new)


def test_copy_good(tmppath):
    """Test move file."""
    fs = XRootDPyFS(mkurl(tmppath))

    src_exists = "data/testa.txt"
    dst_exists = "data/multiline.txt"
    dst_new = "data/ok.txt"
    dst_folder_exists = "data/bfolder/"
    dst_folder_new = "data/anothernewfolder/"
    content = _get_content(fs, src_exists)

    assert fs.exists(dst_exists)
    assert not fs.exists(dst_new)
    assert fs.exists(dst_folder_exists)
    assert not fs.exists(dst_folder_new)

    fs.copy(src_exists, dst_new)
    assert fs.exists(src_exists) and fs.exists(dst_new)

    fs.copy(src_exists, dst_folder_new)
    assert fs.exists(src_exists) and fs.exists(dst_folder_new)

    fs.copy(src_exists, dst_exists, overwrite=True)
    assert fs.exists(src_exists) and fs.exists(dst_exists)
    assert content == _get_content(fs, dst_exists)

    fs.copy(src_exists, dst_folder_exists, overwrite=True)
    assert fs.exists(src_exists) and fs.exists(dst_folder_exists)
    assert content == _get_content(fs, dst_folder_exists)


def test_copy_bad(tmppath):
    """Test copy file."""
    fs = XRootDPyFS(mkurl(tmppath))

    src_exists = "data/testa.txt"
    src_new = "data/testb.txt"
    src_folder_exists = "data/afolder/"
    dst_exists = "data/multiline.txt"
    dst_new = "data/ok.txt"
    dst_folder_exists = "data/bfolder/"
    dst_folder_new = "data/anothernewfolder/"

    # Destination exists
    pytest.raises(DestinationExists, fs.copy, src_exists, dst_exists)
    pytest.raises(DestinationExists, fs.copy, src_exists, src_exists)
    pytest.raises(DestinationExists, fs.copy, src_exists, dst_folder_exists)

    # Cannot copy dir
    pytest.raises(ResourceInvalid, fs.copy, src_folder_exists, dst_new)
    pytest.raises(ResourceInvalid, fs.copy, src_folder_exists, dst_folder_new)

    # Source doesn't exists
    pytest.raises(ResourceNotFound, fs.copy, src_new, dst_exists)
    pytest.raises(ResourceNotFound, fs.copy, src_new, dst_new)
    pytest.raises(ResourceNotFound, fs.copy, src_new, dst_folder_exists)
    pytest.raises(ResourceNotFound, fs.copy, src_new, dst_folder_new)

    pytest.raises(ResourceNotFound, fs.copy, src_new, dst_exists)
    pytest.raises(ResourceNotFound, fs.copy, src_new, dst_new)
    pytest.raises(ResourceNotFound, fs.copy, src_new, dst_folder_exists)
    pytest.raises(ResourceNotFound, fs.copy, src_new, dst_folder_new)


def test_copydir_good(tmppath):
    """Test copy directory."""
    copydir_good(tmppath, False)


def test_copydir_good_parallel(tmppath):
    """Test copy directory."""
    copydir_good(tmppath, True)


def copydir_good(tmppath, parallel):
    """Test copy directory."""
    fs = XRootDPyFS(mkurl(tmppath))

    src_exists = "data/afolder/"
    dst_exists = "data/multiline.txt"
    dst_new = "data/ok.txt"
    dst_folder_exists = "data/bfolder/"
    dst_folder_new = "data/anothernewfolder/"

    assert fs.isdir(src_exists)
    assert fs.exists(dst_exists)
    assert not fs.exists(dst_new)
    assert fs.exists(dst_folder_exists)
    assert not fs.exists(dst_folder_new)

    fs.copydir(src_exists, dst_new, parallel=parallel)
    assert fs.exists(src_exists) and fs.exists(dst_new)

    fs.copydir(src_exists, dst_folder_new, parallel=parallel)
    assert fs.exists(src_exists) and fs.exists(dst_folder_new)

    fs.copydir(src_exists, dst_exists, overwrite=True, parallel=parallel)
    assert fs.exists(src_exists) and fs.exists(dst_exists)
    assert fs.isdir(dst_exists)

    fs.copydir(src_exists, dst_folder_exists, overwrite=True, parallel=parallel)
    assert fs.exists(src_exists) and fs.exists(dst_folder_exists)
    assert fs.isdir(dst_folder_exists)


def test_copydir_bad(tmppath):
    """Test copy directory."""
    copydir_bad(tmppath, False)


def test_copydir_bad_parallel(tmppath):
    """Test copy directory."""
    copydir_bad(tmppath, True)


def copydir_bad(tmppath, parallel):
    """Test copy directory."""
    fs = XRootDPyFS(mkurl(tmppath))

    src_exists = "data/testa.txt"
    src_new = "data/testb.txt"
    src_folder_exists = "data/afolder/"
    src_folder_new = "data/newfolder/"
    dst_exists = "data/multiline.txt"
    dst_new = "data/ok.txt"
    dst_folder_exists = "data/bfolder/"
    dst_folder_new = "data/anothernewfolder/"

    # Destination exists
    pytest.raises(
        DestinationExists, fs.copydir, src_folder_exists, dst_exists, parallel=parallel
    )
    pytest.raises(
        DestinationExists,
        fs.copydir,
        src_folder_exists,
        src_folder_exists,
        parallel=parallel,
    )
    pytest.raises(
        DestinationExists,
        fs.copydir,
        src_folder_exists,
        dst_folder_exists,
        parallel=parallel,
    )

    # Cannot move file
    pytest.raises(ResourceInvalid, fs.copydir, src_exists, dst_new, parallel=parallel)
    pytest.raises(
        ResourceInvalid, fs.copydir, src_exists, dst_folder_new, parallel=parallel
    )

    # Source doesn't exists
    pytest.raises(ResourceNotFound, fs.copydir, src_new, dst_exists, parallel=parallel)
    pytest.raises(ResourceNotFound, fs.copydir, src_new, dst_new, parallel=parallel)
    pytest.raises(
        ResourceNotFound, fs.copydir, src_new, dst_folder_exists, parallel=parallel
    )
    pytest.raises(
        ResourceNotFound, fs.copydir, src_new, dst_folder_new, parallel=parallel
    )

    pytest.raises(
        ResourceNotFound, fs.copydir, src_folder_new, dst_exists, parallel=parallel
    )
    pytest.raises(
        ResourceNotFound, fs.copydir, src_folder_new, dst_new, parallel=parallel
    )
    pytest.raises(
        ResourceNotFound,
        fs.copydir,
        src_folder_new,
        dst_folder_exists,
        parallel=parallel,
    )
    pytest.raises(
        ResourceNotFound, fs.copydir, src_folder_new, dst_folder_new, parallel=parallel
    )


def test_openbin():
    """Test openbin."""
    pytest.raises(NotImplementedError)


def test_setinfo():
    """Test setinfo."""
    pytest.raises(NotImplementedError)
