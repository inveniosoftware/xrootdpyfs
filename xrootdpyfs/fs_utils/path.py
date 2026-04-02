"""Copied from PyFileSystem2, which is licensed under the MIT License."""

import re
import typing

from .errors import IllegalBackReference

if typing.TYPE_CHECKING:
    from typing import List, Text, Tuple

_requires_normalization = re.compile(r"(^|/)\.\.?($|/)|//", re.UNICODE).search


def normpath(path):
    # type: (Text) -> Text
    """Normalize a path.

    This function simplifies a path by collapsing back-references
    and removing duplicated separators.

    Arguments:
        path (str): Path to normalize.

    Returns:
        str: A valid FS path.

    Example:
        >>> normpath("/foo//bar/frob/../baz")
        '/foo/bar/baz'
        >>> normpath("foo/../../bar")
        Traceback (most recent call last):
            ...
        fs.errors.IllegalBackReference: path 'foo/../../bar' contains back-references outside of filesystem

    """  # noqa: E501
    if path in "/":
        return path

    # An early out if there is no need to normalize this path
    if not _requires_normalization(path):
        return path.rstrip("/")

    prefix = "/" if path.startswith("/") else ""
    components = []  # type: List[Text]
    try:
        for component in path.split("/"):
            if component in "..":  # True for '..', '.', and ''
                if component == "..":
                    components.pop()
            else:
                components.append(component)
    except IndexError:
        # FIXME (@althonos): should be raised from the IndexError
        raise IllegalBackReference(path)
    return prefix + "/".join(components)


def isparent(path1, path2):
    # type: (Text, Text) -> bool
    """Check if ``path1`` is a parent directory of ``path2``.

    Arguments:
        path1 (str): A PyFilesytem path.
        path2 (str): A PyFilesytem path.

    Returns:
        bool: `True` if ``path1`` is a parent directory of ``path2``

    Example:
        >>> isparent("foo/bar", "foo/bar/spam.txt")
        True
        >>> isparent("foo/bar/", "foo/bar")
        True
        >>> isparent("foo/barry", "foo/baz/bar")
        False
        >>> isparent("foo/bar/baz/", "foo/baz/bar")
        False

    """
    bits1 = path1.split("/")
    bits2 = path2.split("/")
    while bits1 and bits1[-1] == "":
        bits1.pop()
    if len(bits1) > len(bits2):
        return False
    for bit1, bit2 in zip(bits1, bits2):
        if bit1 != bit2:
            return False
    return True


def frombase(path1, path2):
    # type: (Text, Text) -> Text
    """Get the final path of ``path2`` that isn't in ``path1``.

    Arguments:
        path1 (str): A PyFilesytem path.
        path2 (str): A PyFilesytem path.

    Returns:
        str: the final part of ``path2``.

    Example:
        >>> frombase('foo/bar/', 'foo/bar/baz/egg')
        'baz/egg'

    """
    if not isparent(path1, path2):
        raise ValueError("path1 must be a prefix of path2")
    return path2[len(path1) :]


def isabs(path):
    # type: (Text) -> bool
    """Check if a path is an absolute path.

    Arguments:
        path (str): A PyFilesytem path.

    Returns:
        bool: `True` if the path is absolute (starts with a ``'/'``).

    """
    # Somewhat trivial, but helps to make code self-documenting
    return path.startswith("/")


def abspath(path):
    # type: (Text) -> Text
    """Convert the given path to an absolute path.

    Since FS objects have no concept of a *current directory*, this
    simply adds a leading ``/`` character if the path doesn't already
    have one.

    Arguments:
        path (str): A PyFilesytem path.

    Returns:
        str: An absolute path.

    """
    if not path.startswith("/"):
        return "/" + path
    return path


def relpath(path):
    # type: (Text) -> Text
    """Convert the given path to a relative path.

    This is the inverse of `abspath`, stripping a leading ``'/'`` from
    the path if it is present.

    Arguments:
        path (str): A path to adjust.

    Returns:
        str: A relative path.

    Example:
        >>> relpath('/a/b')
        'a/b'

    """
    return path.lstrip("/")


def join(*paths):
    # type: (*Text) -> Text
    """Join any number of paths together.

    Arguments:
        *paths (str): Paths to join, given as positional arguments.

    Returns:
        str: The joined path.

    Example:
        >>> join('foo', 'bar', 'baz')
        'foo/bar/baz'
        >>> join('foo/bar', '../baz')
        'foo/baz'
        >>> join('foo/bar', '/baz')
        '/baz'

    """
    absolute = False
    relpaths = []  # type: List[Text]
    for p in paths:
        if p:
            if p[0] == "/":
                del relpaths[:]
                absolute = True
            relpaths.append(p)

    path = normpath("/".join(relpaths))
    if absolute:
        path = abspath(path)
    return path


def combine(path1, path2):
    # type: (Text, Text) -> Text
    """Join two paths together.

    This is faster than :func:`~fs.path.join`, but only works when the
    second path is relative, and there are no back references in either
    path.

    Arguments:
        path1 (str): A PyFilesytem path.
        path2 (str): A PyFilesytem path.

    Returns:
        str: The joint path.

    Example:
        >>> combine("foo/bar", "baz")
        'foo/bar/baz'

    """
    if not path1:
        return path2.lstrip()
    return "{}/{}".format(path1.rstrip("/"), path2.lstrip("/"))


def split(path):
    # type: (Text) -> Tuple[Text, Text]
    """Split a path into (head, tail) pair.

    This function splits a path into a pair (head, tail) where 'tail' is
    the last pathname component and 'head' is all preceding components.

    Arguments:
        path (str): Path to split

    Returns:
        (str, str): a tuple containing the head and the tail of the path.

    Example:
        >>> split("foo/bar")
        ('foo', 'bar')
        >>> split("foo/bar/baz")
        ('foo/bar', 'baz')
        >>> split("/foo/bar/baz")
        ('/foo/bar', 'baz')

    """
    if "/" not in path:
        return ("", path)
    split = path.rsplit("/", 1)
    return (split[0] or "/", split[1])


def dirname(path):
    # type: (Text) -> Text
    """Return the parent directory of a path.

    This is always equivalent to the 'head' component of the value
    returned by ``split(path)``.

    Arguments:
        path (str): A PyFilesytem path.

    Returns:
        str: the parent directory of the given path.

    Example:
        >>> dirname('foo/bar/baz')
        'foo/bar'
        >>> dirname('/foo/bar')
        '/foo'
        >>> dirname('/foo')
        '/'

    """
    return split(path)[0]


def basename(path):
    # type: (Text) -> Text
    """Return the basename of the resource referenced by a path.

    This is always equivalent to the 'tail' component of the value
    returned by split(path).

    Arguments:
        path (str): A PyFilesytem path.

    Returns:
        str: the name of the resource at the given path.

    Example:
        >>> basename('foo/bar/baz')
        'baz'
        >>> basename('foo/bar')
        'bar'
        >>> basename('foo/bar/')
        ''

    """
    return split(path)[1]
