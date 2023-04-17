# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015, 2016 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""PyFilesystem opener for XRootD."""

from fs.opener import Opener
from fs.path import split

from .fs import XRootDPyFS
from .utils import spliturl


class XRootDPyOpener(Opener):
    """XRootD PyFilesystem Opener."""

    protocols = ["root", "roots"]

    def open_fs(self, fs_url, parse_result, writeable, create, cwd):
        """Open a filesystem object from a FS URL.

        Arguments:
            fs_url (str): A filesystem URL.
            parse_result (~fs.opener.parse.ParseResult): A parsed filesystem URL.
            writeable (bool): `True` if the filesystem must be writable.
            create (bool): `True` if the filesystem should be created if it does not exist.
            cwd (str): The current working directory (generally only relevant for OS filesystems).

        Raises:
            fs.opener.errors.OpenerError: If a filesystem could not be opened for any reason.

        Returns:
            `~fs.base.FS`: A filesystem instance.
        """
        root_url, path, query = spliturl(fs_url)

        dirpath, _ = split(path)

        fs = XRootDPyFS(root_url + dirpath + query)

        if create and path:
            fs.makedir(path, recursive=True, allow_recreate=True)

        if dirpath:
            fs = fs.opendir(dirpath)

        return fs
