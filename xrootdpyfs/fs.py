# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015, 2016 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""PyFilesystem implementation of XRootD protocol.

:py:class:`XRootDPyFS` is a subclass of PyFilesystem FS class and thus
implements the entire PyFilesystem
`Filesystem interface <http://docs.pyfilesystem.org/en/latest/interface.html>`_
.

.. note::
   All methods prefixed with ``xrd`` in :py:class:`XRootDPyFS` are specific to
   XRootDPyFS and not supported by other PyFilesystem implementations.
"""

import re
from glob import fnmatch

from fs import ResourceType
from fs.base import FS
from fs.errors import (
    DestinationExists,
    DirectoryNotEmpty,
    FSError,
    InvalidPath,
    RemoteConnectionError,
    ResourceError,
    ResourceInvalid,
    ResourceNotFound,
    Unsupported,
)
from fs.info import Info
from fs.path import basename, combine, dirname, frombase, isabs, join, normpath, relpath
from six.moves.urllib.parse import parse_qs, urlencode
from XRootD.client import CopyProcess, FileSystem
from XRootD.client.flags import (
    AccessMode,
    DirListFlags,
    MkDirFlags,
    QueryCode,
    StatInfoFlags,
)

from .utils import is_valid_path, is_valid_url, spliturl
from .xrdfile import XRootDPyFile


class XRootDPyFS(FS):
    """XRootD PyFilesystem interface.

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

    # https://xrootd.slac.stanford.edu/doc/dev52/ofs_config.htm#_Toc53410373
    OSS_TYPE_TO_RESOURCE_TYPE = {
        b"d": ResourceType.directory,
        b"f": ResourceType.file,
    }

    _meta = {
        "case_insensitive": False,
        "network": True,
        "read_only": False,
        "supports_rename": True,
    }

    def __init__(self, url, query=None):
        """Initialize file system object."""
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
        self.queryargs = queryargs
        self._client = FileSystem(self.xrd_get_rooturl())
        super().__init__()

    def _p(self, path, encoding="utf-8"):
        """Prepend base path to path."""
        # fs.path.join() omits the first '/' in self.base_path.
        # It is resolved by adding on an additional '/' to its return value.
        _path = path
        if isabs(path):
            no_trailing = self.base_path[:-1]
            one_slash = no_trailing[1:]
            missing_basepath = not (
                path.startswith(one_slash) or path.startswith(no_trailing)
            )
            if missing_basepath:
                _path = relpath(path)
        return "/" + join(self.base_path, _path)

    def _raise_status(self, path, status):
        """Raise error based on status."""
        # 3006 - legacy (v4 errno), 17 - POSIX error, 3018 (xrootd v5 errno)
        if status.errno in [3006, 17, 3018]:
            raise DestinationExists(path=path, msg=status)
        elif status.errno == 3005:
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

    def listdir(
        self,
        path="./",
        wildcard=None,
        full=False,
        absolute=False,
        dirs_only=False,
        files_only=False,
    ):
        """List the the files and directories under a given path.

        The directory contents are returned as a list of unicode paths.

        :param path: Path to list.
        :type path: str
        :param wildcard: Return only paths that matches the wildcard. It can
            contain a unix filename pattern or a callable that accepts a path
            and returns a boolean
        :type wildcard: str
        :param full: Return full paths (relative to the base path).
        :type full: bool
        :param absolute: Return absolute paths (paths beginning with /)
        :type absolute: bool
        :param dirs_only: If True, return only directories.
        :type dirs_only: bool
        :param files_only: If True, return only files.
        :type files_only: bool

        :returns: Iterable of paths.

        :raises: `fs.errors.ResourceInvalid` if the path exists, but is
            not a directory.
        :raises: `fs.errors.ResourceNotFound` if the path is not found.
        """
        return list(
            self.ilistdir(
                path=path,
                wildcard=wildcard,
                full=full,
                absolute=absolute,
                dirs_only=dirs_only,
                files_only=files_only,
            )
        )

    def _stat_flags(self, path):
        """Get status of a path."""
        status, stat = self._client.stat(self._p(path))

        if not status.ok:
            raise self._raise_status(path, status)
        return stat.flags

    def isdir(self, path, _statobj=None):
        """Check if a path references a directory.

        :param path: a path in the filesystem
        :type path: str

        :rtype: bool

        """
        try:
            flags = self._stat_flags(path) if _statobj is None else _statobj.flags
            return bool(flags & StatInfoFlags.IS_DIR)
        except ResourceNotFound:
            return False

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

    def exists(self, path):
        """Check if a path references a valid resource.

        :param path: A path in the filesystem.
        :type path: str
        :rtype: bool
        """
        status, stat = self._client.stat(self._p(path))
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

        status, _ = self._client.mkdir(self._p(path), flags=flags, mode=mode)

        if not status.ok:
            # 3018 introduced in xrootd5, 17 = POSIX error, 3006 - legacy errno
            destination_exists = status.errno in [3006, 3018, 17]
            if allow_recreate and destination_exists:
                return True
            self._raise_status(path, status)
        return True

    def openbin(self, path, mode="r", buffering=-1, **options):
        """Openbin."""
        raise NotImplementedError

    def remove(self, path):
        """Remove a file from the filesystem.

        :param path: Path of the resource to remove.
        :type path: str

        :raises: `fs.errors.ResourceInvalid` if the path is a directory.
        :raises: `fs.errors.DirectoryNotEmpty` if the directory is not
            empty.
        """
        status, res = self._client.rm(self._p(path))

        if not status.ok:
            self._raise_status(path, status)
        return True

    def removedir(self, path, recursive=False, force=False):
        """Remove a directory from the filesystem.

        :param path: Path of the directory to remove.
        :type path: str
        :param recursive: Unsupported by XRootDPyFS implementation.
        :type recursive: bool
        :param force: If True, any directory contents will be removed
            (recursively). Note that this can be very expensive as the xrootd
            protocol does not support recursive deletes - i.e. the library
            will do a full recursive listing of the directory and send a
            network request per file/directory.
        :type force: bool

        :raises: `fs.errors.DirectoryNotEmpty` if the directory is not
            empty and force is `False`.
        :raises: `fs.errors.ResourceInvalid` if the path is not a
            directory.
        :raises: `fs.errors.ResourceNotFound` if the path does not exist.
        """
        if recursive:
            raise Unsupported("recursive parameter is not supported.")

        status, _ = self._client.rmdir(self._p(path))

        if not status.ok:
            directory_not_empty_error = status.errno == 3005
            if directory_not_empty_error and force:
                # xrootd does not support recursive removal so do we have to
                # do it ourselves.
                for step in self.walk(path, search="depth"):
                    for file in step.files:
                        filepath = join(step.path, file.name)
                        status, _ = self._client.rm(self._p(filepath))
                        if not status.ok:
                            self._raise_status(filepath, status)
                    status, _ = self._client.rmdir(self._p(step.path))
                    if not status.ok:
                        self._raise_status(path, status)
                return True
            self._raise_status(path, status)
        return True

    def setinfo(self, path, info):
        """Set info on a resource."""
        raise NotImplementedError

    def rename(self, src, dst):
        """Rename a file or directory.

        :param src: path to rename.
        :type src: str
        :param dst: new name.
        :type dst: str

        :raises: `fs.errors.DestinationExists` if destination already
            exists.
        :raises: `fs.errors.ResourceNotFound` if source does not exists.
        """
        src = self._p(src)
        dst = self._p(join(dirname(src), dst))

        if not self.exists(src):
            raise ResourceNotFound(src)
        return self._move(src, dst, overwrite=False)

    def getpathurl(self, path, allow_none=False, with_querystring=False):
        """Get URL that corresponds to the given path."""
        if with_querystring and self.queryargs:
            return "{0}{1}?{2}".format(
                self.root_url, self._p(path), urlencode(self.queryargs)
            )
        else:
            return "{0}{1}".format(self.root_url, self._p(path))

    def getinfo(self, path, namespaces=None):
        """Return information for a path as fs.info.Info object.

        The extra namespace `xrootd` contains the following:

        * ``size`` - Number of bytes used to store the file or directory.
        * ``created_time`` - A datetime object containing the time the
           resource was created.
        * ``modified_time`` - A datetime object containing the time the
           resource was modified.
        * ``accessed_time`` - A datetime object containing the time the
           resource was accessed.
        * ``offline`` - True if file/directory is offline.
        * ``writable`` - True if file/directory is writable.
        * ``readable`` - True if file/directory is readable.
        * ``executable`` - True if file/directory is executable.

        :param path: Path to retrieve information about.
        :namespaces list: Info namespaces to query. The
            `"basic"` namespace is alway included in the returned
            info, whatever the value of `namespaces` may be.
        :type path: `string`
        :rtype: `fs.info.Info`
        """
        namespaces = namespaces or ()
        fullpath = self._p(path)
        status, statobj = self._client.stat(fullpath)

        if not status.ok:
            self._raise_status(path, status)

        extended_attr = self._query(QueryCode.XATTR, fullpath)

        is_dir = self.isdir(path, statobj)
        # `basic` namespace
        basic = {
            "name": basename(path),
            "is_dir": is_dir,
        }

        # `details` namespace
        details = {"size": statobj.size, "type": ResourceType.unknown}
        _type = extended_attr.get(b"oss.type", [None])[0]
        if _type:
            details["type"] = self.OSS_TYPE_TO_RESOURCE_TYPE.get(
                _type, ResourceType.unknown
            )

        ct = extended_attr.get(b"oss.ct", [None])[0]
        mt = extended_attr.get(b"oss.mt", [None])[0]
        at = extended_attr.get(b"oss.at", [None])[0]
        if ct:
            details["created"] = int(ct)
        if mt:
            details["modified"] = int(mt)
        if at:
            details["accessed"] = int(at)

        # optional `access` namespace
        access = {
            "permissions": None,  # fs.permissions.Permissions
        }
        uid = extended_attr.get(b"oss.u", [None])[0]
        gid = extended_attr.get(b"oss.u", [None])[0]
        if uid:
            access["uid"] = uid
        if gid:
            access["gid"] = gid

        # other namespaces
        xrootd = {
            "offline": bool(statobj.flags & StatInfoFlags.OFFLINE),
            "writable": bool(statobj.flags & StatInfoFlags.IS_WRITABLE),
            "readable": bool(statobj.flags & StatInfoFlags.IS_READABLE),
            "executable": bool(statobj.flags & StatInfoFlags.X_BIT_SET),
        }

        info = {
            "basic": basic,
        }
        if "details" in namespaces:
            info["details"] = details
        if "stat" in namespaces:
            info["stat"] = {}
        if "lstat" in namespaces:
            info["lstat"] = {}
        if "link" in namespaces:
            info["link"] = {}
        if "access" in namespaces:
            info["access"] = access
        if "xrootd" in namespaces:
            info["xrootd"] = xrootd
        return Info(info)

    def ilistdir(
        self,
        path="./",
        wildcard=None,
        full=False,
        absolute=False,
        dirs_only=False,
        files_only=False,
    ):
        """Generator yielding the files and directories under a given path.

        This method behaves identically to `fs.base:FS.listdir` but
        returns an generator instead of a list.
        """
        flag = DirListFlags.STAT if dirs_only or files_only else DirListFlags.NONE

        full_path = self._p(path)
        status, entries = self._client.dirlist(full_path, flag)

        if not status.ok:
            self._raise_status(path, status)

        return self._ilistdir_helper(
            path,
            entries,
            wildcard=wildcard,
            full=full,
            absolute=absolute,
            dirs_only=dirs_only,
            files_only=files_only,
        )

    def _ilistdir_helper(
        self,
        path,
        entries,
        wildcard=None,
        full=False,
        absolute=False,
        dirs_only=False,
        files_only=False,
    ):
        """A helper method called by ilistdir method that applies filtering.

        Given the path to a directory and a list of the names of entries within
        that directory, this method applies the semantics of the ilistdir()
        keyword arguments. An appropriately modified and filtered list of
        directory entries is returned.
        """
        path = normpath(path)

        if dirs_only and files_only:
            raise ValueError("dirs_only and files_only cannot both be True")

        if wildcard is not None:
            if not callable(wildcard):
                wildcard_re = re.compile(fnmatch.translate(wildcard))

                def wildcard(fn):
                    return bool(wildcard_re.match(fn))

            entries = (p for p in entries if wildcard(p.name))

        if dirs_only:
            entries = (p for p in entries if self.isdir(p.name, _statobj=p.statinfo))
        elif files_only:
            entries = (p for p in entries if self.isfile(p.name, _statobj=p.statinfo))

        if full:
            entries = (combine(path, p.name) for p in entries)
        elif absolute:
            path = self._p(path)
            entries = ((combine(path, p.name)) for p in entries)
        else:
            entries = (p.name for p in entries)

        return entries

    def move(self, src, dst, overwrite=False, **kwargs):
        """Move a file from one location to another.

        :param src: Source path.
        :type src: str
        :param dst: Destination path.
        :type dst: str
        :param overwrite: When True the destination will be overwritten (if it
            exists), otherwise a DestinationExists will be thrown.
        :type overwrite: bool
        :raise: `fs.errors.DestinationExists` if destination exists and
            ``overwrite`` is False.
        :raise: `fs.errors.ResourceInvalid` if source is not a file.
        :raise: `fs.errors.ResourceNotFound` if source was not found.
        """
        src, dst = self._p(src), self._p(dst)

        # isdir/isfile throws an error if file/dir doesn't exists
        if not self.exists(src):
            raise ResourceNotFound(src)

        if not self.isfile(src):
            raise ResourceInvalid(src, msg="Source is not a file: %(path)s")

        return self._move(src, dst, overwrite=overwrite)

    def movedir(self, src, dst, overwrite=False, **kwargs):
        """Move a directory from one location to another.

        :param src: Source directory path.
        :type src: str
        :param dst: Destination directory path.
        :type dst: str
        :param overwrite: When True the destination will be overwritten (if it
            exists), otherwise a DestinationExists will be thrown.
        :type overwrite: bool
        :raise: `fs.errors.DestinationExists` if destination exists and
            `overwrite` is `False`.
        :raise: `fs.errors.ResourceInvalid` if source is not a directory.
        :raise: `fs.errors.ResourceInvalid` if source is a directory and
            destination is a file.
        :raise: `fs.errors.ResourceNotFound` if source was not found.
        """
        src, dst = self._p(src), self._p(dst)

        if not self.exists(src):
            raise ResourceNotFound(src)

        if not self.isdir(src):
            raise ResourceInvalid(src, msg="Source is not a directory: %(path)s")

        return self._move(src, dst, overwrite=overwrite)

    def _move(self, src, dst, overwrite=False):
        """Move source to destination with support for overwriting destination.

        Used by ``XRootDPyFS.move()``, ``XRootDPyFS.movedir()`` and
        ``XRootDPyFS.rename()``.

        .. warning::

           It is the responsibility of the caller of this method to check that
           the source exists.

           If ``overwrite`` is ``True``, this method will first remove any
           destination directory/file if it exists, and then try to move the
           source. Hence, if the source doesn't exists, it will remove the
           destination and then fail.
        """
        if self.exists(dst):
            if not overwrite:
                raise DestinationExists(dst)

            if self.isfile(dst):
                self.remove(dst)
            elif self.isdir(dst):
                self.removedir(dst, force=True)

        status, dummy = self._client.mv(src, dst)

        if not status.ok:
            self._raise_status(dst, status)

        return True

    def copy(self, src, dst, overwrite=False):
        """Copy a file from source to destination.

        :param src: Source path.
        :type src: str
        :param dst: Destination path.
        :type dst: str
        :param overwrite: If True, then an existing file at the destination may
            be overwritten; If False then ``DestinationExists``
            will be raised.
        :type overwrite: bool
        """
        src, dst = self._p(src), self._p(dst)

        # isdir/isfile throws an error if file/dir doesn't exists
        if not self.isfile(src):
            if self.isdir(src):
                raise ResourceInvalid(src, msg="Source is not a file: %(path)s")
            raise ResourceNotFound(src)

        if overwrite and self.exists(dst):
            if self.isdir(dst):
                self.removedir(dst, force=True)

        status, dummy = self._client.copy(src, dst, force=overwrite)

        if not status.ok:
            self._raise_status(dst, status)

        return True

    def copydir(self, src, dst, overwrite=False, parallel=True):
        """Copy a directory from source to destination.

        By default the copy is done by recreating the source directory
        structure at the destination, and then copy files in parallel from
        source to destination.

        :param src: Source directory path.
        :type src: str
        :param dst: Destination directory path.
        :type dst: str
        :param overwrite: If True then any existing files in the destination
            directory will be overwritten.
        :type overwrite: bool
        :param parallel: If True (default), the copy will be done in parallel.
        :type parallel: bool
        """
        if not self.isdir(src):
            if self.isfile(src):
                raise ResourceInvalid(src, msg="Source is not a directory: %(path)s")
            raise ResourceNotFound(src)

        if self.exists(dst):
            if overwrite:
                if self.isdir(dst):
                    self.removedir(dst, force=True)
                elif self.isfile(dst):
                    self.remove(dst)
            else:
                raise DestinationExists(dst)

        if parallel:
            process = CopyProcess()

            def process_copy(src, dst, overwrite=False):
                process.add_job(src, dst)

            copyfile = process_copy
        else:
            copyfile = self.copy

        self.makedir(dst, allow_recreate=True)

        for step in self.walk(src):
            src_dirpath = relpath(step.path)
            dst_dirpath = combine(dst, frombase(src, src_dirpath))
            self.makedir(dst_dirpath, allow_recreate=True, recursive=True)
            for file in step.files:
                src_filepath = join(src_dirpath, file.name)
                dst_filepath = join(dst_dirpath, file.name)
                copyfile(src_filepath, dst_filepath, overwrite=overwrite)

        if parallel:
            process.prepare()
            process.run()

        return True

    #
    # XRootD specific methods.
    #
    @property
    def xrd_client(self):
        """Pyxrootd filesystem client.

        Specific to ``XRootDPyFS``.
        """
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

        value = self._query(QueryCode.CHECKSUM, self._p(path), parse=False)
        value = value.decode("ascii").rstrip("\x00")
        algorithm, value = value.strip().split(" ")
        return (algorithm, value)

    def xrd_ping(self):
        """Ping xrootd server.

        Specific to ``XRootDPyFS``.
        """
        status, dummy = self._client.ping()

        if not status.ok:
            raise RemoteConnectionError(msg=status)

        return True
