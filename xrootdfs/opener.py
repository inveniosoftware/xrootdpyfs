# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""."""

from __future__ import absolute_import, print_function, unicode_literals

from urlparse import urlparse

from fs.opener import Opener, OpenerError, opener
from fs.path import pathsplit

from .fs import XRootDFS
from .utils import is_valid_url


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

        if not is_valid_url(fs_url):
            raise OpenerError('Invalid XRootD URL.')

        scheme, netloc, path, params, query, fragment = urlparse(fs_url)

        root_url = "{scheme}://{netloc}?{query}".format(
            scheme=scheme, netloc=netloc, query=query
        )
        dirpath, resourcepath = pathsplit(path)

        fs = XRootDFS(root_url)

        if create_dir and path:
            fs.makedir(path, recursive=True, allow_recreate=True)

        if dirpath:
            fs = fs.opendir(dirpath)

        if not resourcepath:
            return fs, None
        else:
            return fs, resourcepath

opener.add(XRootDOpener)
