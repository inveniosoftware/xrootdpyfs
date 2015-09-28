# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""Test of XRootDFS."""

from __future__ import absolute_import, print_function

import errno
import math
import sys
from os.path import join

import fs.path
import pytest
from fs import SEEK_CUR, SEEK_END, SEEK_SET
from fs.errors import InvalidPathError, PathError, ResourceNotFoundError, \
    UnsupportedError
from fs.opener import fsopendir, opener
from mock import Mock
from XRootD.client.responses import XRootDStatus

from conftest import mkurl
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


def get_bin_testfile(tmppath):
    fn, fp = 'binary.dat', 'data'
    return get_file_binary(fn, fp, tmppath)


def get_file(fn, fp, tmppath):
    fpp = join(tmppath, fp, fn)
    with opener.open(fpp) as f:
        fc = f.read()
    return {'filename': fn, 'dir': fp, 'contents': fc, 'full_path': fpp}


def get_file_binary(fn, fp, tmppath):
    fpp = join(tmppath, fp, fn)
    with opener.open(fpp, 'rb') as f:
        fc = f.read()
    return {'filename': fn, 'dir': fp, 'contents': fc, 'full_path': fpp}


def copy_file(fn, fp, tmppath):
    path = join(tmppath, fp)
    fn_new = fn + '_copy'
    this_fs = fsopendir(path)
    this_fs.copy(fn, fn_new)
    return fn_new


def get_copy_file(arg, binary=False):
    # Would get called with e.g. arg=get_tsta_file(...)
    fp = fs.path.dirname(arg['full_path'])
    fn_new = copy_file(arg['filename'], '', fp)
    return get_file_binary(fn_new, '', fp) if binary else get_file(
        fn_new, '', fp)


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

    # Mock an error, yayy!
    fake_status = {
        "status": 3,
        "code": 0,
        "ok": False,
        "errno": errno.EREMOTE,
        "error": True,
        "message": '[FATAL] Remote I/O Error',
        "fatal": True,
        "shellcode": 51
    }
    xfile._file.read = Mock(return_value=(XRootDStatus(fake_status), None))
    pytest.raises(IOError, xfile.read)


def test__is_open(tmppath):
    """Test _is_open()"""
    fd = get_tsta_file(tmppath)
    full_path = fd['full_path']
    xfile = XRootDFile(mkurl(full_path))
    assert not xfile.closed
    xfile.close()
    assert xfile.closed


def test_size(tmppath):
    """Tests for the size property size."""
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

    # Mock the error
    fake_status = {
        "status": 3,
        "code": 0,
        "ok": False,
        "errno": errno.EREMOTE,
        "error": True,
        "message": '[FATAL] Remote I/O Error',
        "fatal": True,
        "shellcode": 51
    }
    xfile.close()
    xfile = XRootDFile(mkurl(full_path))
    xfile._file.stat = Mock(return_value=(XRootDStatus(fake_status), None))
    try:
        xfile.size
        assert False
    except IOError:
        assert True


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

    # Negative offsets raise an error
    pytest.raises(IOError, xfile.seek, -1)

    # floating point offsets are converted to integers
    xfile.seek(1.1)
    assert xfile.tell() == 1
    xfile.seek(0.999999)
    assert xfile.tell() == 0


def test_seek_args(tmppath):
    """Test seek() with a non-default whence argument."""
    fd = get_tsta_file(tmppath)
    fb = get_copy_file(fd)
    full_path, fc = fd['full_path'], fd['contents']

    xfile = XRootDFile(mkurl(full_path), 'r+')
    pfile = open(fb['full_path'], 'r+')

    xfile.truncate(3), pfile.truncate(3)
    xfile.seek(2, SEEK_END), pfile.seek(2, SEEK_END)
    assert xfile.tell() == pfile.tell()

    xfile.seek(3, SEEK_CUR), pfile.seek(3, SEEK_CUR)
    assert xfile.tell() == pfile.tell()

    xfile.seek(8, SEEK_SET), pfile.seek(8, SEEK_SET)
    assert xfile.tell() == pfile.tell()

    xfile.truncate(3), pfile.truncate(3)
    xfile.read(), pfile.read()
    assert xfile.tell() == pfile.tell()
    xfile.seek(8, SEEK_END), pfile.seek(8, SEEK_END)
    assert xfile.tell() == pfile.tell()

    xfile.seek(4, SEEK_CUR), pfile.seek(4, SEEK_CUR)
    assert xfile.tell() == pfile.tell()

    pytest.raises(NotImplementedError, xfile.seek, 0, 8)


def test_tell_after_open(tmppath):
    """Tests for tell's init values in the various file modes."""
    fd = get_tsta_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']

    xfile = XRootDFile(mkurl(full_path), 'r')
    assert xfile.tell() == 0
    xfile.close()

    xfile = XRootDFile(mkurl(full_path), 'r+')
    assert xfile.tell() == 0
    xfile.close()

    xfile = XRootDFile(mkurl(full_path), 'r-')
    assert xfile.tell() == 0
    xfile.close()

    xfile = XRootDFile(mkurl(full_path), 'a')
    assert xfile.tell() == len(fc)
    xfile.close()

    xfile = XRootDFile(mkurl(full_path), 'a+')
    assert xfile.tell() == len(fc)
    xfile.close()

    xfile = XRootDFile(mkurl(full_path), 'w')
    assert xfile.tell() == 0
    xfile.close()

    xfile = XRootDFile(mkurl(full_path), 'w-')
    assert xfile.tell() == 0
    xfile.close()


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
    xfile.seek(0)
    assert xfile.read() == '\x00'
    assert xfile.tell() == 1
    xfile.close()

    xfile = XRootDFile(mkurl(full_path), 'r+')
    assert xfile.size == 1
    assert xfile.read() == '\x00'

    # Mock it.
    fake_status = {
        "status": 3,
        "code": 0,
        "ok": False,
        "errno": errno.EREMOTE,
        "error": True,
        "message": '[FATAL] Remote I/O Error',
        "fatal": True,
        "shellcode": 51
    }
    xfile._file.truncate = Mock(return_value=(XRootDStatus(fake_status), None))
    pytest.raises(IOError, xfile.truncate, 0)


def test_truncate2(tmppath):
    """Test truncate(self._size)."""
    fd = get_tsta_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(full_path), 'r+')
    conts = xfile.read()
    assert conts == fc

    newsize = xfile.size
    xfile.truncate(newsize)
    assert xfile.tell() == newsize
    assert xfile.size == len(fc)
    xfile.seek(0)
    assert xfile.read() == conts


def test_truncate3(tmppath):
    """Test truncate(0 < size < self._size)."""
    fd = get_mltl_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(full_path), 'r+')

    initcp = xfile.tell()

    newsiz = len(fc)//2
    xfile.truncate(newsiz)
    assert xfile.tell() == initcp
    xfile.seek(0)  # reset the internal pointer before reading
    assert xfile.read() == fc[:newsiz]


def test_truncate4(tmppath):
    """Verifies that truncate() raises errors on non-truncatable files."""
    fd = get_mltl_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']

    xfile = XRootDFile(mkurl(full_path), 'r')
    pytest.raises(IOError, xfile.truncate, 0)

    xfile.close()
    xfile = XRootDFile(mkurl(full_path), 'w-')
    pytest.raises(IOError, xfile.truncate, 0)


def test_truncate5(tmppath):
    """Test truncate() (no arg)."""
    fd = get_tsta_file(tmppath)
    fb = get_copy_file(fd)
    fp, fc = fd['full_path'], fd['contents']
    fp2 = fb['full_path']

    xfa = XRootDFile(mkurl(fp), 'r+')
    xfb = XRootDFile(mkurl(fp2), 'r+')

    acnts = xfa.read()
    assert acnts == xfb.read()

    # internal pointer starts at 0 in all 'r' modes.
    xtell = xfa.tell()
    assert xfa.tell() == xfb.tell()
    # f.truncate() and f.truncate(self.tell()) should be equivalent
    xfa.truncate(), xfb.truncate(xfb.tell())
    assert xfa.size == xfb.size
    assert xfa.tell() == xtell
    assert xfb.tell() == xtell
    assert xfb.read() == u''
    assert xfa.read() == u''

    xfa.seek(0), xfb.seek(0)
    are = xfa.read()
    assert are == fc
    assert are == xfb.read()


def test_truncate_read_write(tmppath):
    """Tests behaviour of writing after reading after truncating."""
    fd = get_tsta_file(tmppath)
    fb = get_copy_file(fd)
    fp, fc = fd['full_path'], fd['contents']
    fp2 = fb['full_path']

    sp = len(fc)//2
    wstr = "I am the string"

    pfile = open(fp2, 'r+')
    xfile = XRootDFile(mkurl(fp), 'r+')

    xfile.truncate(sp), pfile.truncate(sp)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()
    assert xfile.tell() == pfile.tell()

    xfile.write(wstr), pfile.write(wstr)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()

    xfile.seek(0), pfile.seek(0)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()


def test_truncate_read_write2(tmppath):
    """Tests behaviour of writing after seek(0) after
       reading after truncating."""
    fd = get_tsta_file(tmppath)
    fb = get_copy_file(fd)
    fp, fc = fd['full_path'], fd['contents']
    fp2 = fb['full_path']

    sp = len(fc)//2
    wstr = "I am the string"

    pfile = open(fp2, 'r+')
    xfile = XRootDFile(mkurl(fp), 'r+')

    xfile.truncate(sp), pfile.truncate(sp)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()
    assert xfile.tell() == pfile.tell()

    xfile.seek(0), pfile.seek(0)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()
    xfile.seek(0), pfile.seek(0)

    xfile.write(wstr), pfile.write(wstr)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()
    xfile.seek(0), pfile.seek(0)
    assert xfile.read() == pfile.read()


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

    # run w/ flushing == true
    xfile.write('', True)

    # Mock an error, yayy!
    fake_status = {
        "status": 3,
        "code": 0,
        "ok": False,
        "errno": errno.EREMOTE,
        "error": True,
        "message": '[FATAL] Remote I/O Error',
        "fatal": True,
        "shellcode": 51
    }
    xfile._file.write = Mock(return_value=(XRootDStatus(fake_status), None))
    pytest.raises(IOError, xfile.write, '')


def test_readwrite_unicode(tmppath):
    """Test read/write unicode."""
    if sys.getdefaultencoding() != 'ascii':
        # Python 2 only problem
        raise AssertionError(
            "Default system encoding is not ascii. This is likely due to some"
            " imported module changing it using sys.setdefaultencoding."
        )

    fd = get_tsta_file(tmppath)
    fb = get_copy_file(fd)
    fp, dummy = fd['full_path'], fd['contents']
    fp2 = fb['full_path']

    unicodestr = u"æøå"

    pfile = open(fp2, 'w')
    xfile = XRootDFile(mkurl(fp), 'w')
    pytest.raises(UnicodeEncodeError, pfile.write, unicodestr)
    pytest.raises(UnicodeEncodeError, xfile.write, unicodestr)
    xfile.close()

    xfile = XRootDFile(mkurl(fp), 'w+', encoding='utf-8')
    xfile.write(unicodestr)
    xfile.flush()
    xfile.seek(0)
    assert unicodestr.encode('utf8') == xfile.read()
    xfile.close()

    xfile = XRootDFile(mkurl(fp), 'w+', errors='ignore')
    xfile.write(unicodestr)
    xfile.flush()
    xfile.seek(0)
    assert unicodestr.encode('ascii', 'ignore') == xfile.read()
    xfile.close()


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


def test_init_appendread(tmppath):
    """Test for files opened in mode 'a+'."""
    fd = get_tsta_file(tmppath)
    fp, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(fp), 'a+')
    assert xfile.mode == 'a+'
    assert xfile.tell() == len(fc)
    assert xfile.read() == u''

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


def test_init_newline(tmppath):
    """Tests fs.open() with specified newline parameter."""
    fd = get_tsta_file(tmppath)
    fp, fc = fd['full_path'], fd['contents']

    xfile = XRootDFile(mkurl(fp))
    assert xfile._newline == '\n'
    xfile.close()

    xfile = XRootDFile(mkurl(fp), newline='\n')
    assert xfile._newline == '\n'
    xfile.close()

    pytest.raises(UnsupportedError, XRootDFile, mkurl(fp), mode='r',
                  newline='what')


def test_init_notimplemented(tmppath):
    """Tests that specifying not-implemented args to XRDFile's constructor
       results in an error."""
    fd = get_tsta_file(tmppath)
    fp, fc = fd['full_path'], fd['contents']

    pytest.raises(UnsupportedError, XRootDFile, mkurl(fp), 'rb',
                  buffering=1)
    pytest.raises(NotImplementedError, XRootDFile, mkurl(fp),
                  line_buffering='')


def test_read_errors(tmppath):
    fd = get_tsta_file(tmppath)
    fp, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(fp), 'r')
    xfile.close()
    pytest.raises(ValueError, xfile.read)


def test_read_and_write(tmppath):
    """Tests that the XRDFile behaves like a regular python file."""
    fd = get_tsta_file(tmppath)
    fb = get_copy_file(fd)
    fp, fc = fd['full_path'], fd['contents']
    fp2 = fb['full_path']

    seekpoint = len(fc)//2
    writestr = "Come what may in May this day says Ray all gay like Jay"

    pfile = open(fp2, 'r+')
    xfile = XRootDFile(mkurl(fp), 'r+')

    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()
    assert xfile.tell() == pfile.tell()

    xfile.seek(seekpoint), pfile.seek(seekpoint)
    assert xfile.tell() == pfile.tell()
    xfile.write(writestr), pfile.write(writestr)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()

    xfile.seek(0), pfile.seek(0)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()


def test_write_and_read(tmppath):
    """Tests that the XRootDFile behaves like a regular python file in w+."""
    fd = get_tsta_file(tmppath)
    fb = get_copy_file(fd)
    fp, fc = fd['full_path'], fd['contents']
    fp2 = fb['full_path']

    writestr = "Hello fair mare what fine stairs."
    seekpoint = len(writestr)//2
    # In 'w' (and variant modes) the file's contents are deleted upon opening.

    pfile = open(fp2, 'w+')
    xfile = XRootDFile(mkurl(fp), 'w+')

    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()
    assert xfile.tell() == pfile.tell()

    xfile.write(writestr), pfile.write(writestr)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()
    xfile.seek(0), pfile.seek(0)
    assert xfile.read() == pfile.read()
    assert xfile.tell() == pfile.tell()

    xfile.seek(seekpoint), pfile.seek(seekpoint)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()
    assert xfile.tell() == pfile.tell()


def test_seek_past_eof_rw(tmppath):
    """Tests read/write/truncate behaviour after seeking past the EOF, 'r+'."""
    fd = get_tsta_file(tmppath)
    fb = get_copy_file(fd)
    fp, fc = fd['full_path'], fd['contents']
    fp2 = fb['full_path']

    wstr = "www"
    eof = len(fc)
    skpnt = len(fc)+4

    pfile = open(fp2, 'r+')
    xfile = XRootDFile(mkurl(fp), 'r+')

    xfile.seek(skpnt), pfile.seek(skpnt)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()
    assert xfile.tell() == pfile.tell()
    assert xfile.tell() == skpnt

    xfile.write(wstr), pfile.write(wstr)
    assert xfile.tell() == pfile.tell()
    xfile.seek(eof), pfile.seek(eof)
    assert xfile.read() == pfile.read() == '\x00'*(skpnt-eof) + wstr
    assert xfile.tell() == pfile.tell()

    xfile.seek(0), pfile.seek(0)
    assert xfile.read() == pfile.read()

    xfile.truncate(skpnt), pfile.truncate(skpnt)
    assert xfile.tell() == pfile.tell() == skpnt + len(wstr)

    xfile.write(wstr), pfile.write(wstr)
    expected = fc + '\x00'*(skpnt-eof+len(wstr)) + wstr
    xfile.seek(0), pfile.seek(0)
    assert xfile.read() == pfile.read() == expected


def test_seek_past_eof_wr(tmppath):
    """Tests read/write/truncate behaviour after seeking past the EOF, 'w+'"""
    fd = get_tsta_file(tmppath)
    fb = get_copy_file(fd)
    fp, fc = fd['full_path'], u''
    fp2 = fb['full_path']

    wstr = "www"
    eof = len(fc)
    skpnt = len(fc)+4

    pfile = open(fp2, 'w+')
    xfile = XRootDFile(mkurl(fp), 'w+')

    xfile.seek(skpnt), pfile.seek(skpnt)
    assert xfile.tell() == pfile.tell()
    assert xfile.read() == pfile.read()
    assert xfile.tell() == pfile.tell()
    assert xfile.tell() == skpnt

    xfile.write(wstr), pfile.write(wstr)
    assert xfile.tell() == pfile.tell()
    xfile.seek(eof), pfile.seek(eof)
    assert xfile.read() == pfile.read() == '\x00'*(skpnt-eof) + wstr
    assert xfile.tell() == pfile.tell()

    xfile.seek(0), pfile.seek(0)
    assert xfile.read() == pfile.read()

    xfile.truncate(skpnt), pfile.truncate(skpnt)
    assert xfile.tell() == pfile.tell() == skpnt + len(wstr)

    xfile.write(wstr), pfile.write(wstr)
    expected = fc + '\x00'*(skpnt-eof+len(wstr)) + wstr
    xfile.seek(0), pfile.seek(0)
    assert xfile.read() == pfile.read() == expected


def test_read_binary(tmppath):
    """Tests reading binary data from an existing file."""
    fd = get_bin_testfile(tmppath)
    fb = get_copy_file(fd, binary=True)
    fp, fc = fd['full_path'], fd['contents']
    fp2 = fb['full_path']

    pfile = open(fp2, 'rb')
    xfile = XRootDFile(mkurl(fp), 'rb')

    assert xfile.read() == pfile.read() == fc


def test_write_binary(tmppath):
    """Tests for writing binary data to file."""
    fd = get_bin_testfile(tmppath)
    fp, fc = fd['full_path'], fd['contents']

    # Test w/ confirmed binary data read from a binary file
    xf_new = XRootDFile(mkurl(join(tmppath, 'data/tmp_bin')), 'wb+')
    xf_new.write(fc), xf_new.seek(0)
    assert xf_new.read() == fc

    xf_new.close()
    # Verify persistence.
    xf_new = XRootDFile(mkurl(join(tmppath, 'data/tmp_bin')), 'r+')
    assert xf_new.read() == fc

    # Test truncate
    xf_new.truncate()
    xf_new.seek(0)
    assert xf_new.read() == fc
    xf_new.close()

    # Test with bytearray
    xf_new = XRootDFile(mkurl(join(tmppath, 'data/tmp_bin')), 'wb+')
    barr = bytearray(range(0, 5))
    xf_new.write(barr), xf_new.seek(0)
    assert xf_new.read() == barr
    xf_new.close()

    # Verify persistence.
    xf_new = XRootDFile(mkurl(join(tmppath, 'data/tmp_bin')), 'r')
    assert xf_new.read() == barr
    xf_new.close()


def test_readline(tmppath):
    """Tests for readline()."""
    fd = get_mltl_file(tmppath)
    fb = get_copy_file(fd)
    fp, fc = fd['full_path'], fd['contents']
    fp2 = fb['full_path']

    xfile, pfile = XRootDFile(mkurl(fp), 'r'), opener.open(fp2, 'r')

    assert xfile.readline() == pfile.readline()
    assert xfile.readline() == pfile.readline()
    assert xfile.readline() == pfile.readline()

    xfile.close(), pfile.close()
    xfile, pfile = XRootDFile(mkurl(fp), 'r'), opener.open(fp2, 'r')
    assert xfile.readline() == pfile.readline()
    xfile.seek(0), pfile.seek(0)
    assert xfile.readline() == pfile.readline()
    assert xfile.tell(), pfile.tell()

    xfile.close(), pfile.close()
    xfile = XRootDFile(mkurl(fp), 'w+')

    str1 = 'hello\n'
    str2 = 'bye\n'

    xfile.write(str1+str2)
    xfile.seek(0)
    assert xfile.readline() == str1
    assert xfile.readline() == str2
    assert xfile.readline() == ''
    assert xfile.readline() == ''

    xfile.seek(100)
    assert xfile.readline() == ''

    xfile.close()
    xfile = XRootDFile(mkurl(fp), 'w+')

    xfile.write(str2)
    xfile.seek(len(str2)+1)
    xfile.write(str2)
    xfile.seek(0)
    assert xfile.readline() == str2
    assert xfile.readline() == u'\x00'+str2


def test_flush(tmppath):
    """Tests for flush()"""
    # Mostly it just ensures calling it doesn't crash the program.
    fd = get_tsta_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    xfile = XRootDFile(mkurl(full_path), 'w')

    writestr = 'whut'

    xfile.flush()
    xfile.seek(0, SEEK_END)
    xfile.write(writestr)
    xfile.flush()
    xfile.close()

    xfile = XRootDFile(mkurl(full_path), 'r')
    assert xfile.read() == writestr

    # Fake/mock an error response
    fake_status = {
        "status": 3,
        "code": 0,
        "ok": False,
        "errno": errno.EREMOTE,
        "error": True,
        "message": '[FATAL] Remote I/O Error',
        "fatal": True,
        "shellcode": 51
    }
    # Assign mock return value to the file's sync() function
    # (which is called by flush())
    xfile._file.sync = Mock(return_value=(XRootDStatus(fake_status), None))
    pytest.raises(IOError, xfile.flush)


def test__assert_mode(tmppath):
    """Tests for _assert_mode"""
    fd = get_tsta_file(tmppath)
    full_path, fc = fd['full_path'], fd['contents']
    mode = 'r'
    xfile = XRootDFile(mkurl(full_path), mode)

    assert xfile.mode == mode
    assert xfile._assert_mode(mode)
    delattr(xfile, 'mode')
    pytest.raises(AttributeError, xfile._assert_mode, mode)

    xfile.close()
    xfile = XRootDFile(mkurl(full_path), 'r')
    assert xfile._assert_mode('r')
    pytest.raises(IOError, xfile._assert_mode, 'w')

    xfile.close()
    xfile = XRootDFile(mkurl(full_path), 'w-')
    assert xfile._assert_mode('w-')
    pytest.raises(IOError, xfile._assert_mode, 'r')

    xfile.close()
    xfile = XRootDFile(mkurl(full_path), 'a')
    assert xfile._assert_mode('w')
    pytest.raises(IOError, xfile._assert_mode, 'r')


def test_readlines(tmppath):
    """Tests readlines()"""
    fd = get_mltl_file(tmppath)
    fb = get_copy_file(fd)
    fp, fc = fd['full_path'], fd['contents']
    fp2 = fb['full_path']

    xfile, pfile = XRootDFile(mkurl(fp), 'r'), open(fp2, 'r')

    assert xfile.readlines() == pfile.readlines()

    xfile.seek(0), pfile.seek(0)
    assert pfile.readlines() == xfile.readlines()

    xfile.close(), pfile.close()

    xfile, pfile = XRootDFile(mkurl(fp), 'w+'), open(fp2, 'w+')
    xfile.seek(0), pfile.seek(0)
    assert xfile.readlines() == pfile.readlines()


def test_xreadlines(tmppath):
    """Tests xreadlines()"""
    fp = get_mltl_file(tmppath)['full_path']

    xfile = XRootDFile(mkurl(fp), 'r')

    rl = xfile.readlines()
    xfile.seek(0)
    xl = xfile.xreadlines()
    assert xl != rl
    assert list(xl) == rl


def test_fileno(tmppath):
    """Test fileno."""
    pytest.raises(
        IOError,
        XRootDFile(mkurl(join(tmppath, "data/testa.txt")), 'r-').fileno
    )


def test_name(tmppath):
    """Test name property."""
    assert XRootDFile(mkurl(join(tmppath, "data/testa.txt"))).name == \
        'testa.txt'


def test_isatty(tmppath):
    """Test isatty()."""
    assert XRootDFile(mkurl(join(tmppath, "data/testa.txt"))).isatty() is \
        False


def test_writelines(tmppath):
    """Test writelines()."""
    xfile = XRootDFile(mkurl(join(tmppath, "data/multiline.txt")), 'r')
    yfile = XRootDFile(mkurl(join(tmppath, "data/newfile.txt")), 'w+')
    yfile.writelines(xfile.xreadlines())
    xfile.seek(0), yfile.seek(0)
    assert xfile.readlines() == yfile.readlines()


def test_seekable(tmppath):
    """Test seekable."""
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'r-').seekable() is False
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'r').seekable() is True
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'w').seekable() is True
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'w-').seekable() is False
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'r+').seekable() is True


def test_readable(tmppath):
    """Test seekable."""
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'r-').readable() is True
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'r').readable() is True
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'w').readable() is False
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'r+').readable() is True
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'w+').readable() is True
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'w-').readable() is False


def test_writable(tmppath):
    """Test seekable."""
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'r-').writable() is False
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'r').writable() is False
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'w').writable() is True
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'r+').writable() is True
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'w+').writable() is True
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'w-').writable() is True
    assert XRootDFile(
        mkurl(join(tmppath, "data/testa.txt")), 'a').writable() is True


def test_iterator_buffering(tmppath):
    "Test file iteration."
    f = "data/multiline.txt"
    xfile = XRootDFile(mkurl(join(tmppath, f)), 'r')
    assert len(list(iter(xfile))) == len(open(join(tmppath, f)).readlines())
    xfile = XRootDFile(mkurl(join(tmppath, f)), 'r', buffering=10)
    assert len(list(iter(xfile))) == int(math.ceil(xfile.size / 10.0))
