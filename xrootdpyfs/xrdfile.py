# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015, 2016 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""File-like interface for interacting with files over the XRootD protocol."""

from __future__ import absolute_import, print_function

import sys

from fs import SEEK_CUR, SEEK_END, SEEK_SET
from fs.errors import InvalidPathError, PathError, ResourceNotFoundError, \
    UnsupportedError
from fs.path import basename
from six import b, binary_type, text_type
from XRootD.client import File

from .utils import is_valid_path, is_valid_url, spliturl, \
    translate_file_mode_to_flags


class XRootDPyFile(object):
    r"""File-like interface for working with files over XRootD protocol.

    This class understands and will accept the following mode strings,
    with any additional characters being ignored:

    * ``r`` - Open the file for reading only.
    * ``r+`` - Open the file for reading and writing.
    * ``r-`` - Open the file for streamed reading; do not allow seek/tell.
    * ``w`` - Open the file for writing only; create the file if
      it doesn't exist; truncate it to zero length.
    * ``w+`` - Open the file for reading and writing; create the file
      if it doesn't exist; truncate it to zero length.
    * ``w-`` - Open the file for streamed writing; do not allow seek/tell.
    * ``a`` - Open the file for writing only; create the file if it
      doesn't exist; place pointer at end of file.
    * ``a+`` - Open the file for reading and writing; create the file
      if it doesn't exist; place pointer at end of file.


    .. note::
       Streamed reading/writing modes has no performance advantages over
       non-streamed reading/writing for XRootD.

    :param path: Path to file that should be opened.
    :type path: str
    :param mode: Mode of file to open, identical to the mode string used
        in 'file' and 'open' builtins.
    :type mode: str
    :param buffering: An optional integer used to set the buffering policy.
        Pass 0 to switch buffering off (only allowed in binary mode),
        1 to select line buffering (only usable in text mode), and
        an integer > 1 to indicate the size of a fixed-size chunk buffer.
    :param encoding: Determines encoding used when writing unicode data.
    :param errors: An optional string that specifies how encoding and
        decoding errors are to be handled (e.g. ``strict``, ``ignore`` or
        ``replace``).
    :param newline: Newline character to use (either ``\\n``, ``\\r``,
        ``\\r\\n``, ``''`` or ``None``).
    :param line_buffering: Unsupported. Anything by False will raise and
        error.
    :param buffer_size: Buffer size used when reading files (defaults to 64K).
        This can likely be optimized to chunks up to 2MB depending on your
        desired memory usage.
    """

    def __init__(self, path, mode='r', buffering=-1, encoding=None,
                 errors=None, newline=None, line_buffering=False,
                 buffer_size=None, **kwargs):
        """The XRootDPyFile constructor.

        Raises PathError if the given path isn't a valid XRootD URL,
        and InvalidPathError if it isn't a valid XRootD file path.
        """
        if not is_valid_url(path):
            raise PathError(path)

        xpath = spliturl(path)[1]

        if not is_valid_path(xpath):
            raise InvalidPathError(xpath)

        if newline not in [None, '', '\n', '\r', '\r\n']:
            raise UnsupportedError(
                "Newline character {0} not supported".format(newline))

        if line_buffering is not False:
            raise NotImplementedError("Line buffering for writing is not "
                                      "supported.")

        buffering = int(buffering)
        if buffering == 1 and 'b' in mode:
            raise UnsupportedError(
                "Line buffering is not supported for "
                "binary files.")

        # PyFS attributes
        self.mode = mode

        # XRootD attributes & internals
        self.path = path
        self.encoding = encoding or sys.getdefaultencoding()
        self.errors = errors or 'strict'
        self.buffer_size = buffer_size or 64 * 1024
        self.buffering = buffering
        self._file = File()
        self._ipp = 0
        self._size = -1
        self._iterator = None
        self._newline = newline or b("\n")
        self._buffer = b('')
        self._buffer_pos = 0

        # flag translation
        self._flags = translate_file_mode_to_flags(mode)

        statmsg, response = self._file.open(path, flags=self._flags)

        if not statmsg.ok:
            self._raise_status(self.path, statmsg,
                               "instantiating file ({0})".format(path))

        # Deal with the modes
        if 'a' in self.mode:
            self.seek(self.size, SEEK_SET)

    def _raise_status(self, path, status, source=None):
        """Raise error based on status."""
        if status.errno == 3011:
            raise ResourceNotFoundError(path)
        else:
            if source:
                errstr = "XRootD error {0}file: {1}".format(
                         source + ' ', status.message)
            raise IOError(errstr)

    def __del__(self):
        """Close file on object deletion."""
        self.close()

    def __iter__(self):
        """Initialize the internal iterator."""
        self._next_func = self.read
        self._next_args = ([], dict(sizehint=self.buffer_size))

        if self.buffering == 1 or \
           (self.buffering == -1 and 'b' not in self.mode):
            self._next_func = self.readline
            self._next_args = ([], dict())
        elif self.buffering > 1:
            self._next_args = ([], dict(sizehint=self.buffering))

        return self

    def __enter__(self):
        """Enter context manager method."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit context manager method."""
        self.close()

    def __next__(self):
        """Return next item for file iteration for Python 3."""
        item = self._next_func(*self._next_args[0], **self._next_args[1])
        if not item:
            raise StopIteration
        return item

    def read(self, sizehint=-1):
        """Read ``sizehint`` bytes from the file object.

        If no ``sizehint`` is provided the entire file is read! Multiple calls
        to this method after EOF as been reached, will return an empty string.

        :param sizehint: Number of bytes to read from file object.
        """
        if self.closed:
            raise ValueError("I/O operation on closed file.")

        self._assert_mode("r-")

        chunksize = sizehint if sizehint > 0 else self.size - self._ipp

        if chunksize >= 2147483648:  # 2GB in bytes
                raise IOError(
                    "Chunksize is set to %s which is more than 2GB."
                    "This is not supported!" % chunksize
                )
        elif chunksize < 0:
            chunksize = 1

        # Read data
        statmsg, res = self._file.read(
            offset=self._ipp,
            size=chunksize,
        )

        if not statmsg.ok:
            self._raise_status(self.path, statmsg, "reading")

        # Increment internal file pointer.
        self._ipp = min(
            self._ipp + chunksize,
            self.size if self.size > self._ipp else self._ipp
        )

        return res

    def readline(self):
        """Read one entire line from the file.

        A trailing newline character is kept in the string (but may be absent
        when a file ends with an incomplete line).
        """
        bits = [self._buffer if self._buffer_pos == self.tell() else b("")]
        indx = bits[-1].find(self._newline)

        if indx == -1:
            # Read chunks until first newline is found or entire file is read.
            while indx == -1:
                bit = self.read(self.buffer_size)
                bits.append(bit)
                if not bit:
                    break
                indx = bit.find(self._newline)

        if indx == -1:
            return b("").join(bits)

        indx += len(self._newline)
        extra = bits[-1][indx:]
        bits[-1] = bits[-1][:indx]

        self._buffer = extra
        self._buffer_pos = self.tell()

        return b("").join(bits)

    def readlines(self):
        """Read until EOF using readline().

        .. warning::
           This methods reads the entire file into memory! You are probably
           better off using either ``xreadlines`` or just normal iteration
           over the file object.
        """
        return list(self.xreadlines())

    def xreadlines(self, sizehint=-1):
        """Get an iterator over number of lines."""
        line = True

        while line:
            line = self.readline()
            if not line:
                break
            yield line

    def write(self, data, flushing=False):
        """Write the given string to the file.

        If the keyword argument 'flushing' is true, it indicates that the
        internal write buffers are being flushed, and *all* the given data
        is expected to be written to the file.
        """
        self._assert_mode("w-")

        if 'a' in self.mode:
            self.seek(0, SEEK_END)

        if not isinstance(data, binary_type):
            if isinstance(data, bytearray):
                data = bytes(data)
            elif isinstance(data, text_type):
                data = data.encode(self.encoding, self.errors)

        statmsg, res = self._file.write(data, offset=self._ipp)

        if not statmsg.ok:
            self._raise_status(self.path, statmsg, "writing")

        self._ipp += len(data)
        self._size = max(self.size, self.tell())
        if flushing:
            self.flush()

    def writelines(self, sequence):
        """Write an sequence of lines to file."""
        for s in sequence:
            self.write(s)

    def seek(self, offset, whence=SEEK_SET):
        """Set the file's internal position pointer, approximately.

        The possible values of whence and their meaning are defined
        in the Linux man pages for `lseek()`:
        http://man7.org/linux/man-pages/man2/lseek.2.html

        ``SEEK_SET``
            The internal position pointer is set to offset bytes.
        ``SEEK_CUR``
            The ipp is set to its current position plus offset bytes.
        ``SEEK_END``
            The ipp is set to the size of the file plus offset bytes.
        """
        if "-" in self.mode:
            raise IOError("File is not seekable.")

        # Convert to integer by rounding down/omitting everything after
        # the decimal point
        offset = int(offset)

        # If not in binary mode and seeking from the end, forbid negative
        # offsets
        if not ('b' in self.mode and whence == SEEK_END) and offset < 0:
            raise IOError("Invalid argument.")

        if whence == SEEK_SET:
            self._ipp = offset
        elif whence == SEEK_CUR:
            self._ipp += offset
        elif whence == SEEK_END:
            self._ipp = self.size + offset
        else:
            raise NotImplementedError(whence)

    def tell(self):
        """Get the location of the file's internal position pointer."""
        return self._ipp

    def truncate(self, size=None):
        """Truncate the file's size to ``size``.

        Note that ``size`` will never be None; if it was not specified by the
        user the current file position is used.
        """
        self._assert_mode('w')

        if size is None:
            size = self.tell()

        statmsg = self._file.truncate(size)[0]

        if not statmsg.ok:
            self._raise_status(self.path, statmsg, "truncating")

        self._size = size

    def close(self):
        """Close the file, including flushing the write buffers.

        The file may not be accessed further once it is closed.
        """
        if not self.closed:
            statmsg = self._file.close()[0]

            if not statmsg.ok:
                self._raise_status(self.path, statmsg, "closing")

    def flush(self):
        """Flush write buffers."""
        if not self.closed:
            statmsg, dummy = self._file.sync()
            if not statmsg.ok:
                self._raise_status(self.path, statmsg, "flushing write buffer")

    def seekable(self):
        """Check if file is seekable."""
        return '-' not in self.mode

    def readable(self):
        """Check if file is readable."""
        return 'r' in self.mode or '+' in self.mode

    def writable(self):
        """Check if file is writable."""
        return 'w' in self.mode or '+' in self.mode or 'a' in self.mode

    def isatty(self):
        """Check if file is a TTY (false always).

        Added for ``io`` module compatibility.
        """
        return False

    def fileno(self):
        """Get the underlying file descriptor.

        Unsupported by XRootDPyFS (added for ``io`` module compatibility).
        """
        raise IOError("File descriptor is unsupported by xrootd.")

    @property
    def name(self):
        """Get filename."""
        return basename(self.path)

    @property
    def closed(self):
        """Check if file is closed."""
        return not self._file.is_open()

    @property
    def size(self):
        """Get file size."""
        if self._size == -1:
            statmsg, res = self._file.stat()
            if not statmsg.ok:
                self._raise_status(self.path, statmsg, "retrieving size")
            self._size = res.size
        return self._size

    def _assert_mode(self, mode, mstr=None):
        """Check whether the file may be accessed in the given mode."""
        if mstr is None:
            try:
                mstr = self.mode
            except AttributeError:
                raise AttributeError("Mode attribute missing -- "
                                     "was it deleted? "
                                     "Close and re-open the file.")
        if "+" in mstr:
            return True
        if "-" in mstr and "-" not in mode:
            raise IOError("File does not support seeking.")
        if "r" in mode:
            if "r" not in mstr:
                raise IOError("File not opened for reading")
        if "w" in mode:
            if "w" not in mstr and "a" not in mstr:
                raise IOError("File not opened for writing")
        return True
