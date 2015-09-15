# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""Test of XRootDFS."""

from __future__ import absolute_import, print_function, unicode_literals

from os.path import join

import pytest
from fixture import mkurl, tmppath
from fs.errors import InvalidPathError, PathError, ResourceNotFoundError
from xrootdfs import XRootDFile
from xrootdfs.utils import is_valid_path, is_valid_url


def test_init_basic(tmppath):
    """Test basic initialization of existing file."""

    fname = 'testa.txt'
    fpath = 'data/'
    fcontents = 'testa.txt\n'
    full_fpath = join(tmppath, fpath, fname)
    xfile = XRootDFile(mkurl(full_fpath))
    assert xfile
    assert type(xfile == XRootDFile)
    assert xfile._file
    assert xfile.mode == 'r'

    # Verify that underlying/wrapped file can be read.
    statmsg, res = xfile._file.read()
    assert res == fcontents


def test_init_writemode_basic(tmppath):
    # Non-existing file is created.
    fn, fp, fc = 'nope', 'data/', ''
    full_path = join(tmppath, fp, fn)
    xfile = XRootDFile(mkurl(full_path), mode='w+')
    assert xfile
    assert xfile.read() == fc

    # Existing file is truncated
    fd = get_tsta_file(tmppath)
    full_path = fd['full_path']
    xfile = XRootDFile(mkurl(full_path), mode='w+')
    assert xfile
    assert xfile.read() == ''
    assert xfile.size == 0
    assert xfile.tell() == 0


def test_init_readmode_basic(tmppath):
    # Non-existing file causes what?
    # Resource not found error.
    fn, fp, fc = 'nope', 'data/', ''
    full_path = join(tmppath, fp, fn)
    pytest.raises(ResourceNotFoundError, XRootDFile, mkurl(full_path),
                  mode='r')

    # Existing file can be read?
    fd = get_tsta_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(full_path), mode='r')
    assert xfile
    assert xfile.read() == fc


def get_tsta_file(tmppath):
    fn, fd = 'testa.txt', 'data'
    return get_file(fn, fd, tmppath)


def get_mltl_file(tmppath):
    fn, fp = 'multiline.txt', 'data'
    return get_file(fn, fp, tmppath)


def get_file(fn, fp, tmppath):
    fpp = join(tmppath, fp, fn)
    with open(fpp) as f:
        fc = f.read()
    return {'filename': fn, 'dir': fp, 'contents': fc, 'full_path': fpp}


def test_open_close(tmppath):
    """Test close() on an open file."""
    fd = get_tsta_file(tmppath)
    full_path = fd['full_path']
    xfile = XRootDFile(mkurl(full_path))
    assert xfile
    assert not xfile.closed
    xfile.close()
    assert xfile.closed


def test_read_existing(tmppath):
    """Test read() on an existing non-empty file."""
    fd = get_tsta_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(full_path))

    res = xfile.read()
    assert res == fc
    # After having read the entire file, the file pointer is at the
    # end of the file and consecutive reads return the empty string.
    assert xfile.read() == ''

    # reset ipp to start
    xfile.seek(0)
    assert xfile.read(1) == fc[0]
    assert xfile.read(2) == fc[1:3]
    overflow_read = xfile.read(len(fc))
    assert overflow_read == fc[3:]


def test__is_open(tmppath):
    """Test _is_open()"""
    fd = get_tsta_file(tmppath)
    full_path = fd['full_path']
    xfile = XRootDFile(mkurl(full_path))
    assert not xfile.closed
    xfile.close()
    assert xfile.closed


def test__get_size(tmppath):
    """Tests for __get_size()."""
    fd = get_tsta_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(full_path))

    assert xfile.size == len(fc)

    # Length of empty file
    xfile = XRootDFile(mkurl(join(tmppath, fd['dir'], 'whut')), 'w+')
    assert xfile.size == len('')

    # Length of multiline file
    fd = get_mltl_file(tmppath)
    fpp, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(fpp))
    assert xfile.size == len(fc)


def test_seek_and_tell(tmppath):
    """Basic tests for seek() and tell()."""
    fd = get_tsta_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(full_path))
    assert xfile.tell() == 0

    # Read file, then check the internal position pointer.
    conts = xfile.read()
    assert xfile.tell() == len(fc)
    assert conts == fc

    # Seek to beginning, then verify ipp.
    xfile.seek(0)
    assert xfile.tell() == 0
    assert xfile.read() == fc

    newpos = len(fc)//2
    xfile.seek(newpos)
    conts2 = xfile.read()
    assert conts2 == conts[newpos:]
    assert xfile.tell() == len(fc)

    # # Now with a multiline file!
    fd = get_mltl_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(full_path))

    assert xfile.tell() == 0
    newpos = len(fc)//3
    xfile.seek(newpos)
    assert xfile.tell() == newpos
    nconts = xfile.read()
    assert xfile.tell() == len(fc)
    assert nconts == fc[newpos:]


def test_truncate1(tmppath):
    """Test truncate(0)."""
    fd = get_tsta_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(full_path), 'r+')
    # r+ opens for r/w, and won't truncate the file automatically.
    assert xfile.read() == fc
    assert xfile.tell() == len(fc)
    xfile.seek(0)  # Reset ipp.
    assert xfile.tell() == 0

    # Truncate it to size 0.
    xfile.truncate(0)
    assert xfile.size == 0
    assert xfile.tell() == 0
    assert xfile.read() == ''
    assert xfile.tell() == 0
    xfile.close()

    # Re-open same file.
    xfile = XRootDFile(mkurl(full_path), 'r+')
    assert xfile.size == 0
    assert xfile.read() == ''

    # Truncate it again!
    xfile.truncate(0)
    assert xfile.size == 0
    assert xfile.read() == ''

    # Truncate it twice.
    xfile.truncate(0)
    assert xfile.size == 0
    assert xfile.read() == ''

    # Truncate to 1.
    xfile.truncate(1)
    assert xfile.tell() == 0
    assert xfile.size == 1
    assert xfile.read() == '\x00'
    assert xfile.tell() == 1
    xfile.close()

    xfile = XRootDFile(mkurl(full_path), 'r+')
    assert xfile.size == 1
    assert xfile.read() == '\x00'


def test_truncate2(tmppath):
    """Test truncate(self._size)."""
    fd = get_tsta_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(full_path), 'r+')
    conts = xfile.read()
    assert conts == fc

    xfile.truncate(xfile.size)
    assert xfile.tell() == 0
    assert xfile.size == len(fc)
    assert xfile.read() == conts


def test_truncate3(tmppath):
    """Test truncate(0 < size < self._size)."""
    fd = get_mltl_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(full_path), 'r+')

    newsiz = len(fc)//2
    xfile.truncate(newsiz)
    assert xfile.tell() == 0
    assert xfile.read() == fc[:-newsiz]


def test_write(tmppath):
    """Test write()."""
    # With a new file.
    xfile = XRootDFile(mkurl(join(tmppath, 'data/nuts')), 'w+')
    assert xfile.size == 0
    conts = xfile.read()
    assert not conts

    nconts = 'Write.'
    xfile.write(nconts)
    assert xfile.tell() == len(nconts)
    assert not xfile.closed
    xfile.seek(0)
    assert xfile.size == len(nconts)
    assert xfile.read() == nconts
    xfile.close()

    # Verify persistence after closing.
    xfile = XRootDFile(mkurl(join(tmppath, 'data/nuts')), 'r+')
    assert xfile.size == len(nconts)
    assert xfile.read() == nconts

    # Seek(x>0) followed by a write
    nc2 = 'hello'
    cntr = len(nconts)//2
    xfile.seek(cntr)
    xfile.write(nc2)
    assert xfile.tell() == len(nc2) + cntr
    xfile.seek(0)
    assert xfile.read() == nconts[:cntr] + nc2
    xfile.close()

    # Seek(x>0) followed by a write of len < size-x
    fd = get_tsta_file(tmppath)
    fp, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(fp), 'r+')
    assert xfile.read() == fc
    xfile.seek(2)
    nc = 'yo'
    xfile.write(nc)
    assert xfile.tell() == len(nc) + 2
    assert xfile.read() == fc[2+len(nc):]


def test_init_paths(tmppath):
    """Tests how __init__ responds to correct and invalid paths."""
    # Invalid url should raise error
    url = "fee-fyyy-/fooo"
    assert not is_valid_url(url) \
        and pytest.raises(PathError, XRootDFile, url)

    path = '//ARGMEGXXX//\\///'
    assert not is_valid_path(path) \
        and pytest.raises(InvalidPathError, XRootDFile, mkurl(path))


def test_init_append(tmppath):
    """Test for files opened 'a'"""
    fd = get_tsta_file(tmppath)
    fp, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(fp), 'a')
    assert xfile.mode == 'a'
    pytest.raises(IOError, xfile.read)
    assert xfile.tell() == len(fc)

    # Seeking is allowed, but writes still go on the end.
    xfile.seek(0)
    assert xfile.tell() == 0
    newcont = u'butterflies'
    xfile.write(newcont)
    assert xfile.tell() == len(fc) + len(newcont)
    # Can't read in this mode.
    xfile.close()
    xfile = XRootDFile(mkurl(fp), 'r')
    assert xfile.read() == fc + newcont

    xfile.close()
    xfile = XRootDFile(mkurl(fp), 'a')
    xfile.write(fc)
    xfile.seek(0)
    pytest.raises(IOError, xfile.read)


def test_init_append(tmppath):
    """Test for files opened in mode 'a+'."""
    fd = get_tsta_file(tmppath)
    fp, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(fp), 'a+')
    assert xfile.mode == 'a+'
    assert xfile.read() == fc
    assert xfile.tell() == len(fc)

    # Seeking is allowed, but writes still go on the end.
    xfile.seek(0)
    assert xfile.tell() == 0
    newcont = u'butterflies'
    xfile.write(newcont)
    assert xfile.tell() == len(fc) + len(newcont)
    xfile.seek(0)
    assert xfile.read() == fc + newcont
    xfile.write(fc)
    xfile.seek(0)
    xfile.read() == fc + newcont + fc


def test_init_writemode(tmppath):
    """Tests for opening files in 'w(+)'"""
    fd = get_tsta_file(tmppath)
    fp, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(fp), 'w')
    pytest.raises(IOError, xfile.read)

    xfile.seek(1)
    conts = 'what'
    xfile.write(conts)
    assert xfile.tell() == 1 + len(conts)
    assert xfile.size == 1 + len(conts)
    xfile.close()
    xfile = XRootDFile(mkurl(fp), 'r')
    fc = xfile.read()
    assert fc == '\x00'+conts
    assert not fc == conts


def test_init_streammodes(tmppath):
    fd = get_tsta_file(tmppath)
    fp, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(fp), 'r-')
    pytest.raises(IOError, xfile.seek, 3)
    assert xfile.size == len(fc)
    assert xfile.tell() == 0
    assert xfile.read() == fc
    assert xfile.tell() == len(fc)

    xfile.close()
    xfile = XRootDFile(mkurl(fp), 'w-')
    pytest.raises(IOError, xfile.read)
    pytest.raises(IOError, xfile.seek, 3)
    assert xfile.tell() == 0
    assert xfile.size == 0
    conts = 'hugs are delightful'
    xfile.write(conts)
    assert xfile.tell() == len(conts)
    xfile.close()
    xfile = XRootDFile(mkurl(fp), 'r')
    assert xfile.read() == conts


def test_read_errors(tmppath):
    fd = get_tsta_file(tmppath)
    fp, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(fp), 'r')
    xfile.close()
    pytest.raises(ValueError, xfile.read)
