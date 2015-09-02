# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""Filesystem class."""

from __future__ import absolute_import, print_function, unicode_literals

import re
from glob import fnmatch

from fs.base import FS
from fs.errors import DestinationExistsError, DirectoryNotEmptyError, \
    FSError, InvalidPathError, ResourceInvalidError, UnsupportedError
from fs.path import normpath, pathcombine, pathjoin
from XRootD.client import FileSystem
from XRootD.client.flags import AccessMode, DirListFlags, MkDirFlags, \
    OpenFlags, StatInfoFlags

from .utils import is_valid_path, is_valid_url, spliturl
from .xrdfile import XRootDFile


class XRootDFS(FS):

    """."""

    _meta = {
        'thread_safe': True,
        'virtual': False,
        'read_only': False,
        'unicode_paths': True,
        'case_insensitive_paths': False,
        'network': True,
        'atomic.move': True,
        'atomic.copy': True,
        'atomic.makedir': True,
        'atomic.rename': False,
        'atomic.setcontents': True
    }

    def __init__(self, url, query=None, timeout=0, thread_synchronize=True):
        """."""
        if not is_valid_url(url):
            raise InvalidPathError(path=url)

        root_url, base_path, queryargs = spliturl(url)

        if not is_valid_path(base_path):
            raise InvalidPathError(path=base_path)

        self.timeout = timeout
        self.root_url = root_url
        self.base_path = base_path
        self.query = queryargs or query
        self.client = FileSystem(root_url)
        super(XRootDFS, self).__init__(thread_synchronize=thread_synchronize)

    def _p(self, path):
        """Join path to base path."""
        # fs.path.pathjoin() omits the first '/' in self.base_path.
        # It is resolved by adding on an additional '/' to its return value.
        return '/' + pathjoin(self.base_path, path)

    def open(self, path, mode='r', buffering=-1, encoding=None, errors=None,
             newline=None, line_buffering=False, **kwargs):
        """Open a the given path as a file-like object.

        :param path: a path to file that should be opened
        :type path: string
        :param mode: mode of file to open, identical to the mode string used
            in 'file' and 'open' builtins
        :type mode: string
        :param kwargs: additional (optional) keyword parameters that may
            be required to open the file
        :type kwargs: dict

        :rtype: a file-like object

        :raises `fs.errors.ParentDirectoryMissingError`: if an intermediate
            directory is missing
        :raises `fs.errors.ResourceInvalidError`: if an intermediate directory
            is an file
        :raises `fs.errors.ResourceNotFoundError`: if the path is not found
        """
        # path must be full-on address with the server and everything, yo.
        fpath = self.root_url + self._p(path)
        return XRootDFile(fpath, mode, buffering, encoding, errors, newline,
                          line_buffering, **kwargs)

    def listdir(self,
                path="./",
                wildcard=None,
                full=False,
                absolute=False,
                dirs_only=False,
                files_only=False):
        """List the the files and directories under a given path.

        The directory contents are returned as a list of unicode paths.

        :param path: root of the path to list
        :type path: string
        :param wildcard: only returns paths that match this wildcard
        :type wildcard: string containing a wildcard, or a callable that
            accepts a path and returns a boolean
        :param full: returns full paths (relative to the root)
        :type full: bool
        :param absolute: returns absolute paths (paths beginning with /)
        :type absolute: bool
        :param dirs_only: if True, only return directories
        :type dirs_only: bool
        :param files_only: if True, only return files
        :type files_only: bool

        :rtype: iterable of paths

        :raises `fs.errors.ParentDirectoryMissingError`: if an intermediate
            directory is missing
        :raises `fs.errors.ResourceInvalidError`: if the path exists, but is
            not a directory
        :raises `fs.errors.ResourceNotFoundError`: if the path is not found
        """
        return list(self.ilistdir(
            path=path, wildcard=wildcard, full=full, absolute=absolute,
            dirs_only=dirs_only, files_only=files_only
        ))

    def _stat_flags(self, path):
        """Get status of a path."""
        status, stat = self.client.stat(self._p(path))

        if not status.ok:
            raise InvalidPathError(path=path, details=status)
        return stat.flags

    def isdir(self, path, _statobj=None):
        """Check if a path references a directory.

        :param path: a path in the filesystem
        :type path: string

        :rtype: bool

        """
        flags = self._stat_flags(path) if _statobj is None else _statobj
        return bool(flags & StatInfoFlags.IS_DIR)

    def isfile(self, path, _statobj=None):
        """Check if a path references a file.

        :param path: a path in the filesystem
        :type path: string

        :rtype: bool

        """
        flags = self._stat_flags(path) if _statobj is None else _statobj
        return not bool(flags & (StatInfoFlags.IS_DIR | StatInfoFlags.OTHER))

    def exists(self, path):
        """Check if a path references a valid resource.

        :param path: A path in the filesystem.
        :type path: string
        :rtype: bool
        """
        status, stat = self.client.stat(self._p(path))
        return status.ok

    def makedir(self, path, recursive=False, allow_recreate=False):
        """Make a directory on the filesystem.

        :param path: path of directory
        :type path: string
        :param recursive: if True, any intermediate directories will also be
            created
        :type recursive: bool
        :param allow_recreate: if True, re-creating a directory wont be an
            error
        :type allow_create: bool

        :raises `fs.errors.DestinationExistsError`: if the path is already a
            existing, and allow_recreate is False
        :raises `fs.errors.ParentDirectoryMissingError`:
        :raises `fs.errors.ResourceInvalidError`: if a containing
            directory is missing and recursive is False or if a path is an
            existing file
        """
        flags = MkDirFlags.MAKEPATH if recursive else MkDirFlags.NONE
        mode = AccessMode.NONE

        status, res = self.client.mkdir(self._p(path), flags=flags, mode=mode)

        if status.ok or (allow_recreate and status.errno == 3006):
            return True

        self._raise_status(path, status)

    def _raise_status(self, path, status):
        """Raise error based on status."""
        if status.errno == 3006:
            raise DestinationExistsError(path=path, details=status)
        elif status.errno == 3005:
            raise DirectoryNotEmptyError(path=path, details=status)
        elif status.errno == 3011:
            raise ResourceInvalidError(path=path, details=status)
        else:
            raise FSError(details=status)

    def remove(self, path):
        """Remove a file from the filesystem.

        :param path: Path of the resource to remove
        :type path: string

        :raises `fs.errors.ResourceInvalidError`: if the path is a directory
        :raises `fs.errors.DirectoryNotEmptyError`: if the directory is not
            empty
        """
        status, res = self.client.rm(self._p(path))

        if status.ok:
            return True

        self._raise_status(path, status)

    def removedir(self, path, recursive=False, force=False):
        """Remove a directory from the filesystem.

        :param path: path of the directory to remove
        :type path: string
        :param recursive: if True, empty parent directories will be removed
        :type recursive: bool
        :param force: if True, any directory contents will be removed
        :type force: bool

        :raises `fs.errors.DirectoryNotEmptyError`: if the directory is not
            empty and force is False
        :raises `fs.errors.ParentDirectoryMissingError`: if an intermediate
            directory is missing
        :raises `fs.errors.ResourceInvalidError`: if the path is not a
            directory
        :raises `fs.errors.ResourceNotFoundError`: if the path does not exist
        """
        status, res = self.client.rmdir(self._p(path))
        if not status.ok:
            raise FSError(details=status)
        return True

    def rename(self, src, dst):
        """Rename a file or directory.

        :param src: path to rename
        :type src: string
        :param dst: new name
        :type dst: string

        :raises ParentDirectoryMissingError: if a containing directory is
            missing
        :raises ResourceInvalidError: if the path or a parent path is not a
            directory or src is a parent of dst or one of src or dst is a dir
            and the other don't
        :raises ResourceNotFoundError: if the src path does not exist

        """
        raise UnsupportedError("rename resource")

    def getinfo(self, path):
        """Return information for a path as a dictionary.

        The exact content of this dictionary will vary depending on the
        implementation, but will likely include a few common values. The
        following values will be found in info dictionaries for most
        implementations:

         * "size" - Number of bytes used to store the file or directory
         * "created_time" - A datetime object containing the time the resource
            was created
         * "accessed_time" - A datetime object containing the time the resource
            was last accessed
         * "modified_time" - A datetime object containing the time the resource
            was modified

        :param path: a path to retrieve information for
        :type path: string

        :rtype: dict

        :raises `fs.errors.ParentDirectoryMissingError`: if an intermediate
            directory is missing
        :raises `fs.errors.ResourceInvalidError`: if the path is not a
            directory
        :raises `fs.errors.ResourceNotFoundError`: if the path does not exist
        """
        raise UnsupportedError("get resource info")

    def ilistdir(self,
                 path="./",
                 wildcard=None,
                 full=False,
                 absolute=False,
                 dirs_only=False,
                 files_only=False):
        """Generator yielding the files and directories under a given path.

        This method behaves identically to :py:meth:`fs.base.FS.listdir` but
        returns an generator instead of a list.  Depending on the filesystem
        this may be more efficient than calling :py:meth:`fs.base.FS.listdir`
        and iterating over the resulting list.
        """
        flag = DirListFlags.STAT if dirs_only or files_only else \
            DirListFlags.NONE

        full_path = self._p(path)
        status, entries = self.client.dirlist(
            full_path, flag, timeout=self.timeout)

        if not status.ok:
            raise InvalidPathError(path=path, details=status)

        return self._ilistdir_helper(
            path, entries, wildcard=wildcard, full=full,
            absolute=absolute, dirs_only=dirs_only, files_only=files_only
        )

    def _ilistdir_helper(self, path, entries, wildcard=None, full=False,
                         absolute=False, dirs_only=False, files_only=False):
        """A helper method called by ilistdir method that applies filtering.

        Given the path to a directory and a list of the names of entries within
        that directory, this method applies the semantics of the ilistdir()
        keyword arguments. An appropriately modified and filtered list of
        directory entries is returned.
        """
        path = normpath(path)

        if dirs_only and files_only:
            raise ValueError("dirs_only and files_only can not both be True")

        if wildcard is not None:
            if not callable(wildcard):
                wildcard_re = re.compile(fnmatch.translate(wildcard))

                def wildcard(fn):
                    return bool(wildcard_re.match(fn))

            entries = (p for p in entries if wildcard(p.name))

        if dirs_only:
            entries = (
                p for p in entries if self.isdir(p.name, _statobj=p.statinfo)
            )
        elif files_only:
            entries = (
                p for p in entries if self.isfile(p.name, _statobj=p.statinfo)
            )

        if full:
            entries = (pathcombine(path, p.name) for p in entries)
        elif absolute:
            path = self._p(path)
            entries = ((pathcombine(path, p.name)) for p in entries)
        else:
            entries = (p.name for p in entries)

        return entries
