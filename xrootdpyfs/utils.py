# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""Helper methods for working with root URLs."""

from __future__ import absolute_import, print_function

import re

from six.moves.urllib.parse import urlparse
from XRootD.client import URL
from XRootD.client.flags import OpenFlags


def is_valid_url(fs_url):
    """Check if URL is a valid root URL."""
    scheme, netloc, path, params, query, fragment = urlparse(fs_url)
    return URL(fs_url).is_valid() and scheme in ['root', 'roots']


def is_valid_path(fs_path):
    """Check if path is a valid XRootD compatible path.

    Valid paths start with two slashes ('/'), i.e. '//';
    and do not contain any other two adjacent slashes.
    """
    if len(fs_path) > 1:
        if not re.search(r'^//', fs_path) or re.search(r'//', fs_path[1:]):
            return False
        else:
            return True
    else:
        return False


def spliturl(fs_url):
    """Split XRootD URL in a host and path part."""
    scheme, netloc, path, params, query, fragment = urlparse(fs_url)

    pattern = "{scheme}://{netloc}"

    root_url = pattern.format(
        scheme=scheme, netloc=netloc
    )

    return root_url, path, query


def translate_file_mode_to_flags(mode='r'):
    """Translate a PyFS mode string to a combination of XRootD OpenFlags."""
    flags = 0
    if 'r+' in mode or 'a' in mode:
        return OpenFlags.UPDATE
    if 'w' in mode:
        return OpenFlags.DELETE
    if 'r' in mode:
        return OpenFlags.READ

    return flags
