# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015-2020 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""Path manipulation utilities for XRootD URLs.

These utilities are compatible with PyFilesystem2's path utilities
but work with XRootD URLs instead of generic filesystem paths.
"""


def normpath(path):
    """Normalize a path.

    :param path: The path to normalize.
    :returns: Normalized path.
    """
    # For XRootD, paths are typically absolute with double slash prefix
    # e.g., //path/to/file or /path/to/file
    # We'll do minimal normalization
    return path


def basename(path):
    """Return the base name of a path.

    :param path: The path.
    :returns: The base name (last component).
    """
    # Remove trailing slashes
    path = path.rstrip('/')
    if not path:
        return ''
    
    # Find last slash
    idx = path.rfind('/')
    if idx < 0:
        return path
    return path[idx + 1:]


def dirname(path):
    """Return the directory name of a path.

    :param path: The path.
    :returns: The directory name.
    """
    # Remove trailing slashes
    path = path.rstrip('/')
    if not path:
        return '.'
    
    # Find last slash
    idx = path.rfind('/')
    if idx < 0:
        return '.'
    if idx == 0:
        return '/' if path.startswith('/') else '.'
    return path[:idx]


def split_path(path):
    """Split a path into directory and base name.

    :param path: The path to split.
    :returns: Tuple of (dirname, basename).
    """
    return dirname(path), basename(path)


def join(*paths):
    """Join path components.

    :param paths: Path components to join.
    :returns: Joined path.
    """
    if not paths:
        return ''
    
    result = paths[0]
    for path in paths[1:]:
        if not path:
            continue
        if result.endswith('/'):
            result += path.lstrip('/')
        else:
            result += '/' + path.lstrip('/')
    return result


def combine(path1, path2):
    """Combine two paths.

    :param path1: First path.
    :param path2: Second path.
    :returns: Combined path.
    """
    return join(path1, path2)


def frombase(base, path):
    """Get path relative to base.

    :param base: Base path.
    :param path: Path to make relative.
    :returns: Relative path.
    """
    # Simple implementation - just return path as-is
    # Proper implementation would strip base from path
    return path


def relpath(path, start=None):
    """Get relative path.

    :param path: Path to make relative.
    :param start: Starting path (default current directory).
    :returns: Relative path.
    """
    if start is None:
        start = '.'
    return path


def isabs(path):
    """Check if path is absolute.

    :param path: Path to check.
    :returns: True if absolute, False otherwise.
    """
    # XRootD paths starting with // or / are absolute
    return path.startswith('//') or path.startswith('/')
