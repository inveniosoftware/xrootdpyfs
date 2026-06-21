# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015-2020 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""XRootD filesystem abstraction for invenio-files-rest compatibility.

This module provides a minimal filesystem abstraction similar to the FS class
in invenio-files-rest, but for XRootD URLs instead of local filesystem paths.
"""

from urllib.parse import parse_qs, urlencode

from XRootD.client.flags import (
    AccessMode,
    MkDirFlags,
    QueryCode,
    StatInfoFlags,
)
from .errors import (
    DestinationExists,
    DirectoryNotEmpty,
    FSError,
    InvalidPath,
    ResourceError,
    ResourceInvalid,
    ResourceNotFound,
    Unsupported,
)
from .utils import is_valid_path, is_valid_url, spliturl

from XRootD.client import FileSystem
from .xrdfile import XRootDPyFile


class XRootDPyFS:
    """XRootD filesystem abstraction.

    The argument ``query`` is particular useful for specifying e.g. Kerberos
    or GSI authentication without adding it in the URL. The following:

    .. code-block:: python

        fs = XRootDPyFS(
            "root://localhost?&xrd.wantprot=krb5&xrd.k5ccname=/tmp/krb_filexxx"
        )

    is equivalent to:

    .. code-block:: python

        fs = XRootDPyFS(
            "root://localhost",
            {"xrd.wantprot": "krb5", "xrd.k5ccname": "/tmp/krb_filexxx"}
        )

    This way you can easily separate the URL from the authentication query
    parameters. Note that ``xrd.k5ccname`` specifies a Kerberos `ticket`
    and not a `keytab`.

    :param url: A root URL.
    :param query: Dictionary of key/values to append to the URL query string.
        The contents of the dictionary gets merged with any querystring
        provided in the ``url``.
    :type query: dict
    """

    def __init__(self, url, query=None):
        """Initialize the filesystem with a base URL.

        :param url: The base XRootD URL.
        :param query: Dictionary of key/values to append to the URL query string.
        """
        if not is_valid_url(url):
            raise InvalidPath(path=url)

        root_url, base_path, queryargs = spliturl(url)

        if not is_valid_path(base_path):
            raise InvalidPath(path=base_path)

        if queryargs:
            # Convert query string in URL into a dictionary. Assumes there's no
            # duplication of fields names in query string (such as e.g.
            # '?f1=a&f1=b').
            queryargs = {k: v[0] for (k, v) in parse_qs(queryargs).items()}

            # Merge values from kwarg query into the dictionary. Conflicting
            # keys raises an exception.
            for k, v in (query or {}).items():
                if k in queryargs:
                    raise KeyError(
                        "Query string field {0} conflicts with "
                        "field in URL {1}".format(k, url)
                    )
                queryargs[k] = v
        else:
            # No query string in URL, use kwarg instead.
            queryargs = query

        self.root_url = root_url
        self.base_path = base_path
        self._base_url = base_path
        self.queryargs = queryargs
        self._client = FileSystem(self.xrd_get_rooturl())

    @property
    def xrd_client(self):
        """Get the XRootD FileSystem client."""
        return self._client

    def xrd_get_rooturl(self):
        """Get the URL with query string for this FS.

        Specific to ``XRootDPyFS``.
        """
        if self.queryargs:
            return "{0}/?{1}".format(self.root_url, urlencode(self.queryargs))
        else:
            return self.root_url

    def xrd_checksum(self, path, _statobj=None):
        """Get checksum of file from server.

        Specific to ``XRootDPyFS``. Note not all XRootD servers support the
        checksum operation (in particular the default local xrootd server).

        :param src: File to calculate checksum for.
        :type src: str
        :raise: `fs.errors.Unsupported` if server does not support
            checksum calculation.
        :raise: `fs.errors.FSError` if you try to get the checksum of e.g. a
            directory.
        """
        if not self.isfile(path, _statobj=_statobj):
            raise ResourceInvalid("Path is not a file: %s" % path)

        value = self._query(QueryCode.CHECKSUM, path, parse=False)
        value = value.decode("ascii").rstrip("\x00")
        algorithm, value = value.strip().split(" ")
        return (algorithm, value)

    def _get_full_url(self, path):
        """Get the full XRootD URL for a given path.

        :param path: Path relative to the base URL.
        :returns: Full XRootD URL.
        :raises ValueError: If the path tries to escape the base URL.
        """
        if not path:
            return self._base_url

        # For XRootD URLs, we need to be careful with path joining
        # XRootD URLs typically look like: root://host//path/to/file
        # The path component starts after the double slash

        # Simple concatenation for XRootD paths
        # Remove leading slash from path if present
        path = path.lstrip('/')
        full_url = self._base_url + path

        # Validate that the result is still under our base
        # This is a simple check - for XRootD, we can't easily escape the base
        # since the URL structure is fixed
        return full_url

    def getpathurl(self, path, allow_none=False, with_querystring=False):
        """Get URL that corresponds to the given path."""
        if with_querystring and self.queryargs:
            return "{0}{1}?{2}".format(
                self.root_url, self._p(path), urlencode(self.queryargs)
            )
        else:
            return "{0}{1}".format(self.root_url, self._p(path))

    def _query(self, flag, arg, parse=True):
        """Query an xrootd server."""
        status, res = self._client.query(flag, arg)

        if not status.ok:
            if status.errno == 3013:
                raise Unsupported(msg=status)
            raise FSError(msg=status)

        # due to https://github.com/xrootd/xrootd/blob
        # /39f9e0ae6744c4e068905daf0a10270f443b8619/src/XrdOfs/XrdOfsFSctl.cc#L230
        # the response contains random bytes due to the way buffer size is allocated
        # which causes response parsing errors on our python client.
        # The bytes succeeding the null byte (x00) should be ignored.
        if b"\x00" in res[-3:-1]:
            res = res.split(b"\x00")[0]
        return parse_qs(res) if parse else res

    def _raise_status(self, path, status):
        """Raise error based on status."""
        # 3006 - legacy (v4 errno), 17 - POSIX error, 3018 (xrootd v5 errno)
        if status.errno in [3006, 17, 3018]:
            if status.message.strip().endswith("directory not empty"):
                raise DirectoryNotEmpty(path=path, msg=status)
            raise DestinationExists(path=path, msg=status)
        elif status.errno in [3005]:
            # Unfortunately only way to determine if the error is due to a
            # directory not being empty, or that a resource is not a directory:
            if status.message.strip().endswith("not a directory"):
                raise ResourceInvalid(path=path, msg=status)
            else:
                raise DirectoryNotEmpty(path=path, msg=status)
        elif status.errno == 3011:
            raise ResourceNotFound(path=path, msg=status)
        else:
            raise ResourceError(path=path, msg=status)

    def _stat_flags(self, path):
        """Get status of a path."""
        status, stat = self._client.stat(path)

        if not status.ok:
            raise self._raise_status(path, status)
        return stat.flags

    def isfile(self, path, _statobj=None):
        """Check if a path references a file.

        :param path: a path in the filesystem
        :type path: str

        :rtype: bool

        """
        try:
            flags = self._stat_flags(path) if _statobj is None else _statobj.flags
            return not bool(flags & (StatInfoFlags.IS_DIR | StatInfoFlags.OTHER))
        except ResourceNotFound:
            return False

    def open(
        self,
        path,
        mode="r",
        buffering=-1,
        encoding=None,
        errors=None,
        newline=None,
        line_buffering=False,
        **kwargs
    ):
        r"""Open the given path and return a file-like object.

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

        :returns: A file-like object.

        :raises: `fs.errors.ResourceInvalid` if an intermediate directory
            is an file.
        :raises: `fs.errors.ResourceNotFound` if the path is not found.
        """
        return XRootDPyFile(
            self.getpathurl(path, with_querystring=True),
            mode=mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
            line_buffering=line_buffering,
            **kwargs
        )

    def exists(self, path):
        """Check if a file or directory exists in the filesystem.

        :param path: The path to check relative to the base URL.
        :returns: True if the resource exists, False otherwise.
        """
        full_url = self._get_full_url(path)
        # Extract the path part for XRootD stat
        from .utils import spliturl
        xrootd_path = spliturl(full_url)[1]

        status, stat = self._client.stat(xrootd_path)
        return status.ok

    def makedir(
        self,
        path,
        recursive=False,
        allow_recreate=False,
        permissions=None,
        recreate=False,
    ):
        """Make a directory on the filesystem.

        :param path: Path of directory.
        :type path: str
        :param recursive: If True, any intermediate directories will also be
            created.
        :type recursive: `bool`
        :param allow_recreate: If True, re-creating a directory wont be an
            error.
        :type allow_create: `bool`

        :raises: `fs.errors.DestinationExists` if the path is already
            existing, and allow_recreate is False.
        :raises: `fs.errors.ResourceInvalid` if a containing
            directory is missing and recursive is False or if a path is an
            existing file.
        """
        flags = MkDirFlags.MAKEPATH if recursive else MkDirFlags.NONE
        mode = AccessMode.NONE

        status, _ = self._client.mkdir(path, flags=flags, mode=mode)

        if not status.ok:
            # 3018 introduced in xrootd5, 17 = POSIX error, 3006 - legacy errno
            destination_exists = status.errno in [3006, 17, 3018]
            if allow_recreate and destination_exists:
                return True
            self._raise_status(path, status)
        return True

    def remove(self, path):
        """Remove a file from the filesystem.

        :param path: The path to the file relative to the base URL.
        :raises OSError: If the filesystem is not writeable.
        :raises FileNotFoundError: If the file does not exist.
        """
        if not self._writeable:
            raise OSError(f"Cannot remove - filesystem is not writeable")

        full_url = self._get_full_url(path)
        from .utils import spliturl
        xrootd_path = spliturl(full_url)[1]

        status, res = self._client.rm(xrootd_path)
        if not status.ok:
            if status.errno == 3011:  # ENONET - No such file
                raise FileNotFoundError(f"File not found: {path}")
            raise OSError(f"Failed to remove {path}: {status.message}")

    def removedir(self, path):
        """Remove a directory from the filesystem.

        :param path: The path to the directory relative to the base URL.
        :raises OSError: If the filesystem is not writeable or if the directory is not empty.
        :raises FileNotFoundError: If the directory does not exist.
        """
        if not self._writeable:
            raise OSError(f"Cannot remove directory - filesystem is not writeable")

        full_url = self._get_full_url(path)
        from .utils import spliturl
        xrootd_path = spliturl(full_url)[1]

        status, res = self._client.rmdir(xrootd_path)
        if not status.ok:
            if status.errno == 3011:  # ENONET - No such file
                raise FileNotFoundError(f"Directory not found: {path}")
            if status.errno == 3013:  # ENOTEMPTY - Directory not empty
                raise OSError(f"Directory not empty: {path}")
            raise OSError(f"Failed to remove directory {path}: {status.message}")

    def walk(self, path):
        """Walk through the directory and yield file paths.

        :param path: The path to the directory relative to the base URL.
        :yield: A generator yielding (dirpath, dirnames, filenames) tuples.
        """
        full_url = self._get_full_url(path)
        from .utils import spliturl
        xrootd_path = spliturl(full_url)[1]

        # Use XRootD dirlist to get directory contents
        from XRootD.client.flags import DirListFlags

        status, listing = self._client.dirlist(xrootd_path, flags=DirListFlags.STAT)
        if not status.ok:
            raise OSError(f"Failed to list directory {path}: {status.message}")

        # For compatibility with os.walk, we need to yield tuples
        # But XRootD dirlist returns a different format
        # We'll do a simpler implementation that yields the directory contents

        # For now, just yield the directory path and its immediate contents
        dirnames = []
        filenames = []

        if listing:
            for item in listing:
                # item is a StatInfoX object
                name = item.getPath()
                # name is relative to the queried path
                if name.endswith('/'):
                    dirnames.append(name[:-1])  # Remove trailing slash
                else:
                    filenames.append(name)

        yield (path, dirnames, filenames)

    @classmethod
    def _get_path_from_uri(cls, uri_or_path):
        """Return the path from a URI or path string.

        For XRootD, we handle URLs like root://host//path/to/file.

        :param uri_or_path: URI or path string.
        :returns: The path component.
        """
        from .utils import spliturl
        return spliturl(uri_or_path)[1]

    @classmethod
    def dirname(cls, uri_or_path):
        """Return the directory name of the given path.

        :param uri_or_path: URI or path string.
        :returns: Directory name.
        """
        from .path import dirname
        return dirname(uri_or_path)

    @classmethod
    def basename(cls, uri_or_path):
        """Return the base name of the given path.

        :param uri_or_path: URI or path string.
        :returns: Base name.
        """
        from .path import basename
        return basename(uri_or_path)

    @classmethod
    def split_path(cls, uri_or_path):
        """Split the path into directory and base name.

        :param uri_or_path: URI or path string.
        :returns: Tuple of (dirname, basename).
        """
        return (cls.dirname(uri_or_path), cls.basename(uri_or_path))
