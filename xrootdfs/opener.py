# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""PyFilesystem opener for XRootD."""

from __future__ import absolute_import, print_function

from fs.opener import Opener, opener
from fs.path import pathsplit

from .fs import XRootDFS
from .utils import spliturl


class XRootDOpener(Opener):

    """XRootD PyFilesystem Opener."""

    names = ["root", "roots"]
    desc = """Opens a filesystem via the XRootD protocol."""

    @classmethod
    def get_fs(cls, registry, fs_name, fs_name_params, fs_path, writeable,
               create_dir):
        """.

        :param fs_name: the name of the opener, as extracted from the protocol
            part of the url,
        :param fs_name_params: reserved for future use
        :param fs_path: the path part of the url
        :param writeable: if True, then get_fs must return an FS that can be
            written to
        :param create_dir: if True then get_fs should attempt to silently
            create the directory references in path
        """
        fs_url = "{0}://{1}".format(fs_name, fs_path)

        root_url, path, query = spliturl(fs_url)

        dirpath, resourcepath = pathsplit(path)

        fs = XRootDFS(root_url + dirpath + query)

        if create_dir and path:
            fs.makedir(path, recursive=True, allow_recreate=True)

        if dirpath:
            fs = fs.opendir(dirpath)

        if not resourcepath:
            return fs, None
        else:
            return fs, resourcepath


opener.add(XRootDOpener)
