# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""Helper methods for working with root URLs."""

from __future__ import absolute_import, print_function, unicode_literals

from urlparse import urlparse

from fs.errors import FSError
from XRootD.client import URL


def is_valid_url(fs_url):
    """Check if URL is a valid root URL."""
    scheme, netloc, path, params, query, fragment = urlparse(fs_url)
    return URL(fs_url).is_valid() and scheme in ['root', 'roots']


def spliturl(fs_url):
    """Split XRootD URL in a host and path part."""
    if not is_valid_url(fs_url):
        raise FSError("Invalid XRootD URL: %s" % fs_url)

    scheme, netloc, path, params, query, fragment = urlparse(fs_url)

    if query:
        pattern = "{scheme}://{netloc}/?{query}"
    else:
        pattern = "{scheme}://{netloc}/"

    root_url = pattern.format(
        scheme=scheme, netloc=netloc, query=query
    )

    if path == "/":
        path = ""

    return root_url, path
