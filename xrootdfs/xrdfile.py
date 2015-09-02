# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""."""

from __future__ import absolute_import, print_function, unicode_literals

import fs
import fs.filelike
from fs import SEEK_CUR, SEEK_END, SEEK_SET
from fs.errors import InvalidPathError, PathError, ResourceNotFoundError
from XRootD.client import File as XFile

from .utils import is_valid_path, is_valid_url, spliturl, \
    translate_file_mode_to_flags


class XRootDFile(fs.filelike.FileLikeBase):
    """Wrapper-like class for XRootD file objects.

    This class understands and will accept the following mode strings,
    with any additional characters being ignored:

        * r    - open the file for reading only.
        * r+   - open the file for reading and writing.
        * r-   - open the file for streamed reading; do not allow seek/tell.
        * w    - open the file for writing only; create the file if
                 it doesn't exist; truncate it to zero length.
        * w+   - open the file for reading and writing; create the file
                 if it doesn't exist; truncate it to zero length.
        * w-   - open the file for streamed writing; do not allow seek/tell.
        * a    - open the file for writing only; create the file if it
                 doesn't exist; place pointer at end of file.
        * a+   - open the file for reading and writing; create the file
                 if it doesn't exist; place pointer at end of file.

    These are mostly standard except for the "-" indicator, which has
    been added for efficiency purposes in cases where seeking can be
    expensive to simulate (e.g. compressed files).  Note that any file
    opened for both reading and writing must also support seeking.
    """

    def __init__(self, path, mode='r', buffering=-1, encoding=None,
                 errors=None, newline=None, line_buffering=False, **kwargs):
        """XRootDFile constructor.

        Raises PathError if the given path isn't a valid XRootD URL,
        and InvalidPathError if it isn't a valid XRootD file path.
        """
        if not is_valid_url(path):
            raise PathError(path)

        xpath = spliturl(path)[1]

        if not is_valid_path(xpath):
            raise InvalidPathError(xpath)

        super(XRootDFile, self).__init__()

        # PyFS attributes
        self.mode = mode

        # XRootD attributes & internals
        self._file = XFile()
        self._ipp = 0
        self._timeout = 0
        self._callback = None
        self._fullpath = path

        self._size = 0

        # flag translation
        self._flags = translate_file_mode_to_flags(mode)

        status, response = self._file.open(self._fullpath, self._flags)
        if not status.ok:
            if status.errno == 3011:
                raise ResourceNotFoundError(self._fullpath)
            else:
                raise IOError("Error returned by XRootD server while trying to \
                               instantiate file.", {'message': status.message,
                                                    'file': self._fullpath})
        else:
            self._size = self._file.stat()[1].size

        # Deal with the modes
        if self.mode == 'a':
            self._seek(self._size, SEEK_SET)

    def _read(self, sizehint=-1):
        """Read approximately <sizehint> bytes from the file-like object.

        This method is to be implemented by subclasses that wish to be
        readable.  It should read approximately <sizehint> bytes from the
        file and return them as a string.  If <sizehint> is missing or
        less than or equal to zero, try to read all the remaining contents.

        The method need not guarantee any particular number of bytes -
        it may return more bytes than requested, or fewer.  If needed the
        size hint may be completely ignored.  It may even return an empty
        string if no data is yet available.

        Because of this, the method must return None to signify that EOF
        has been reached.  The higher-level methods will never indicate EOF
        until None has been read from _read().  Once EOF is reached, it
        should be safe to call _read() again, immediately returning None.
        """
        if self._tell() == self._size:
            return None

        statmsg, res = self._file.read(self._ipp)
        self._seek(len(res), SEEK_CUR)
        return res

    def _write(self, string, flushing=False):
        """Write the given string to the file-like object.

        This method must be implemented by subclasses wishing to be writable.
        It must attempt to write as much of the given data as possible to the
        file, but need not guarantee that it is all written.  It may return
        None to indicate that all data was written, or return as a string any
        data that could not be written.

        If the keyword argument 'flushing' is true, it indicates that the
        internal write buffers are being flushed, and *all* the given data
        is expected to be written to the file. If unwritten data is returned
        when 'flushing' is true, an IOError will be raised.
        """
        if 'a' in self.mode:
            self._seek(0, SEEK_END)

        statmsg, res = self._file.write(string, self._ipp)
        if statmsg.ok and not statmsg.error:
            self._seek(len(string), SEEK_CUR)
            self._size = max(self._size, self._tell())
            return None
        else:
            raise IOError(("Error writing to file: {0}".format(
                           statmsg.message), self))

    def _seek(self, offset, whence):
        """Set the file's internal position pointer, approximately.

        This method should set the file's position to approximately 'offset'
        bytes relative to the position specified by 'whence'.  If it is
        not possible to position the pointer exactly at the given offset,
        it should be positioned at a convenient *smaller* offset and the
        file data between the real and apparent position should be returned.

        At minimum, this method must implement the ability to seek to
        the start of the file, i.e. offset=0 and whence=0.  If more
        complex seeks are difficult to implement then it may raise
        NotImplementedError to have them simulated (inefficiently) by
        the higher-level machinery of this class.

        The possible values of whence and their meaning are defined
        in the Linux man pages for `lseek()`:
        http://man7.org/linux/man-pages/man2/lseek.2.html

        SEEK_SET
            The internal position pointer is set to offset bytes.
        SEEK_CUR
            The ipp is set to its current position plus offset bytes.
        SEEK_END
            The ipp is set to the size of the file plus offset bytes.
        """
        if whence == SEEK_SET:
            self._ipp = offset
            return

        if whence == SEEK_CUR:
            self._ipp += offset
            return

        if whence == SEEK_END:
            self._ipp = self._size + offset
            return

        raise NotImplementedError(whence)

    def _tell(self):
        """Get the location of the file's internal position pointer.

        This method must be implemented by subclasses that wish to be
        seekable, and must return the position of the file's internal
        pointer.

        Due to buffering, the position seen by users of this class
        (the "apparent position") may be different to the position
        returned by this method (the "actual position").
        """
        return self._ipp

    def _truncate(self, size):
        """Truncate the file's size to <size>.

        This method must be implemented by subclasses that wish to be
        truncatable.  It must truncate the file to exactly the given size
        or fail with an IOError.

        Note that <size> will never be None; if it was not specified by the
        user then it is calculated as the file's apparent position (which may
        be different to its actual position due to buffering).
        """
        statmsg = self._file.truncate(size)[0]
        if not statmsg.ok or statmsg.error:
            raise IOError((statmsg.message, self))
        else:
            self._seek(size, SEEK_SET)
            self._size = size

    def _get_size(self):
        """Get current size of file as reported by the XRootD server it is
        on."""
        return self._size

    def _is_open(self):
        """Checks if the wrapped XRootD-File object is open."""
        return self._file.is_open()

    def close(self):
        """Flush write buffers and close the file.

        The file may not be accessed further once it is closed.
        """
        if not self.closed:
            super(XRootDFile, self).close()
            if self._file.is_open():
                self._file.close()
