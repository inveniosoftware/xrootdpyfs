# SPDX-FileCopyrightText: 2015, 2023 CERN.
# SPDX-License-Identifier: BSD-3-Clause

"""Minimal PyFilesystem compatibility layer.

This module provides a minimal compatibility layer to replace the PyFilesystem
 dependency. It contains only the classes and utilities that are actually used
by XRootDPyFS.
"""

import posixpath
import re
from collections import defaultdict, deque, namedtuple
from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum, IntEnum

# ============================================================================
# Enums
# ============================================================================


class ResourceType(Enum):
    """Resource type enumeration."""

    file = 1
    directory = 2
    unknown = 3


class Seek(IntEnum):
    """Seek mode enumeration."""

    set = 0
    current = 1
    end = 2


# ============================================================================
# Error Classes
# ============================================================================


class FSError(Exception):
    """Base class for filesystem errors."""

    def __init__(self, msg=None, path=None):
        """Initialize error.

        :param msg: Error message.
        :param path: Path related to the error.
        """
        self.msg = msg
        self.path = path
        if msg and path:
            super().__init__("{0}: {1}".format(path, msg))
        elif msg:
            super().__init__(msg)
        elif path:
            super().__init__(path)
        else:
            super().__init__()


class ResourceNotFound(FSError):
    """Resource not found error."""

    pass


class ResourceInvalid(FSError):
    """Resource invalid error."""

    pass


class ResourceError(FSError):
    """Resource error."""

    pass


class DestinationExists(FSError):
    """Destination already exists error."""

    pass


class DirectoryNotEmpty(FSError):
    """Directory not empty error."""

    pass


class InvalidPath(FSError):
    """Invalid path error."""

    pass


class RemoteConnectionError(FSError):
    """Remote connection error."""

    pass


class Unsupported(FSError):
    """Unsupported operation error."""

    pass


class PathError(OSError):
    """Path error."""

    pass


class IllegalBackReference(ValueError):
    """Too many backrefs exist in a path.

    This error will occur if the back references in a path would be
    outside of the root. For example, ``"/foo/../../"``, contains two back
    references which would reference a directory above the root.

    Note:
        This exception is a subclass of `ValueError` as it is not
        strictly speaking an issue with a filesystem or resource.

    """

    def __init__(self, path):
        """Constructor."""
        self.path = path
        msg = ("path '{path}' contains back-references outside of filesystem").format(
            path=path
        )
        super(IllegalBackReference, self).__init__(msg)

    def __reduce__(self):
        """Reduce."""
        return type(self), (self.path,)


class MissingInfoNamespace(AttributeError):
    """An expected namespace is missing."""

    def __init__(self, namespace):
        """Constructor."""
        self.namespace = namespace
        msg = "namespace '{}' is required for this attribute"
        super().__init__(msg.format(namespace))

    def __reduce__(self):
        """Reduce."""
        return type(self), (self.namespace,)


# ============================================================================
# Path Utilities
# ============================================================================


def abspath(path):
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


def basename(path):
    """Get the basename of a path.

    :param path: The path.
    :return: The basename.
    """
    """Return the basename of the resource referenced by a path.

    This is always equivalent to the 'tail' component of the value
    returned by split(path).

    Arguments:
        path (str): A PyFilesytem path.

    Returns:
        str: the name of the resource at the given path.
    """
    return split(path)[1]


def dirname(path):
    """Return the parent directory of a path.

    This is always equivalent to the 'head' component of the value
    returned by ``split(path)``.

    Arguments:
        path (str): A PyFilesytem path.

    Returns:
        str: the parent directory of the given path.
    """
    return split(path)[0]


def join(*paths):
    """Join any number of paths together.

    Arguments:
        *paths (str): Paths to join, given as positional arguments.

    Returns:
        str: The joined path.
    """
    absolute = False
    relpaths = []
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


_requires_normalization = re.compile(r"(^|/)\.\.?($|/)|//", re.UNICODE).search


def normpath(path):
    """Normalize a path.

    This function simplifies a path by collapsing back-references
    and removing duplicated separators.

    Arguments:
        path (str): Path to normalize.

    Returns:
        str: A valid FS path.
    """  # noqa: E501
    if path in "/":
        return path

    # An early out if there is no need to normalize this path
    if not _requires_normalization(path):
        return path.rstrip("/")

    prefix = "/" if path.startswith("/") else ""
    components = []
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


def isabs(path):
    """Check if a path is absolute.

    :param path: The path.
    :return: True if absolute, False otherwise.
    """
    return posixpath.isabs(path)


def relpath(path, start=None):
    """Convert the given path to a relative path.

    This is the inverse of `abspath`, stripping a leading ``'/'`` from
    the path if it is present.

    Arguments:
        path (str): A path to adjust.

    Returns:
        str: A relative path.
    """
    return path.lstrip("/")


def split(path):
    """Split a path into (head, tail) pair.

    This function splits a path into a pair (head, tail) where 'tail' is
    the last pathname component and 'head' is all preceding components.

    Arguments:
        path (str): Path to split

    Returns:
        (str, str): a tuple containing the head and the tail of the path.
    """
    if "/" not in path:
        return ("", path)
    split = path.rsplit("/", 1)
    return (split[0] or "/", split[1])


def isparent(path1, path2):
    """Check if ``path1`` is a parent directory of ``path2``.

    Arguments:
        path1 (str): A PyFilesytem path.
        path2 (str): A PyFilesytem path.

    Returns:
        bool: `True` if ``path1`` is a parent directory of ``path2``
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
    """Get the final path of ``path2`` that isn't in ``path1``.

    Arguments:
        path1 (str): A PyFilesytem path.
        path2 (str): A PyFilesytem path.

    Returns:
        str: the final part of ``path2``.
    """
    if not isparent(path1, path2):
        raise ValueError("path1 must be a prefix of path2")
    return path2[len(path1) :]


def combine(path1, path2):
    """Join two paths together.

    This is faster than :func:`~fs.path.join`, but only works when the
    second path is relative, and there are no back references in either
    path.

    Arguments:
        path1 (str): A PyFilesytem path.
        path2 (str): A PyFilesytem path.

    Returns:
        str: The joint path.
    """
    if not path1:
        return path2.lstrip()
    return "{}/{}".format(path1.rstrip("/"), path2.lstrip("/"))


def make_repr(class_name, *args, **kwargs):
    """Generate a repr string.

    Positional arguments should be the positional arguments used to
    construct the class. Keyword arguments should consist of tuples of
    the attribute value and default. If the value is the default, then
    it won't be rendered in the output.
    """
    arguments = [repr(arg) for arg in args]
    arguments.extend(
        [
            "{}={!r}".format(name, value)
            for name, (value, default) in sorted(kwargs.items())
            if value != default
        ]
    )
    return "{}({})".format(class_name, ", ".join(arguments))


def epoch_to_datetime(t):
    """Convert epoch time to a UTC datetime."""
    if t is None:
        return None
    return datetime.fromtimestamp(t, tz=timezone.utc)


# ============================================================================
# Walker Class
# ============================================================================


Step = namedtuple("Step", "path, dirs, files")


class Walker:
    """A walker object recursively lists directories in a filesystem."""

    def __init__(
        self,
        ignore_errors=False,
        on_error=None,
        search="breadth",
        filter=None,
        exclude=None,
        filter_dirs=None,
        exclude_dirs=None,
        max_depth=None,
        filter_glob=None,
        exclude_glob=None,
    ):
        """Create a new `Walker` instance.

        Arguments:
            ignore_errors (bool): If `True`, any errors reading a
                directory will be ignored, otherwise exceptions will
                be raised.
            on_error (callable): If ``ignore_errors`` is `False`,
                then this callable will be invoked for a path and the
                exception object. It should return `True` to ignore the error,
                or `False` to re-raise it.
            search (str): If ``"breadth"`` then the directory will be
                walked *top down*. Set to ``"depth"`` to walk *bottom up*.
            filter (list): If supplied, this parameter should be
                a list of filename patterns, e.g. ``["*.py"]``. Files will
                only be returned if the final component matches one of the
                patterns.
            exclude (list): If supplied, this parameter should be
                a list of filename patterns, e.g. ``["~*"]``. Files matching
                any of these patterns will be removed from the walk.
            filter_dirs (list): A list of patterns that will be used
                to match directories names. The walk will only open directories
                that match at least one of these patterns. Directories will
                only be returned if the final component matches one of the
                patterns.
            exclude_dirs (list): A list of patterns that will be
                used to filter out directories from the walk. e.g.
                ``['*.svn', '*.git']``. Directory names matching any of these
                patterns will be removed from the walk.
            max_depth (int): Maximum directory depth to walk.
            filter_glob (list): If supplied, this parameter
                should be a list of path patterns e.g. ``["foo/**/*.py"]``.
                Resources will only be returned if their global path or
                an extension of it matches one of the patterns.
            exclude_glob (list): If supplied, this parameter
                should be a list of path patterns e.g. ``["foo/**/*.pyc"]``.
                Resources will not be returned if their global path or
                an extension of it  matches one of the patterns.

        """
        if search not in ("breadth", "depth"):
            raise ValueError("search must be 'breadth' or 'depth'")
        self.ignore_errors = ignore_errors
        if on_error:
            if ignore_errors:
                raise ValueError("on_error is invalid when ignore_errors==True")
        else:
            on_error = self._ignore_errors if ignore_errors else self._raise_errors
        if not callable(on_error):
            raise TypeError("on_error must be callable")

        self.on_error = on_error
        self.search = search
        self.filter = filter
        self.exclude = exclude
        self.filter_dirs = filter_dirs
        self.exclude_dirs = exclude_dirs
        self.filter_glob = filter_glob
        self.exclude_glob = exclude_glob
        self.max_depth = max_depth
        super().__init__()

    @classmethod
    def _ignore_errors(cls, path, error):
        """Ignore dir scan errors when called."""
        return True

    @classmethod
    def _raise_errors(cls, path, error):
        """Re-raise dir scan errors when called."""
        return False

    @classmethod
    def _calculate_depth(cls, path):
        """Calculate the 'depth' of a directory path (i.e. count components)."""
        _path = path.strip("/")
        return _path.count("/") + 1 if _path else 0

    @classmethod
    def bind(cls, fs):
        """Bind a `Walker` instance to a given filesystem.

        This *binds* in instance of the Walker to a given filesystem, so
        that you won't need to explicitly provide the filesystem as a
        parameter.

        Arguments:
            fs (FS): A filesystem object.

        Returns:
            ~fs.walk.BoundWalker: a bound walker.
        """
        return BoundWalker(fs)

    def __repr__(self):
        """Return a string representation of the walker."""
        return make_repr(
            self.__class__.__name__,
            ignore_errors=(self.ignore_errors, False),
            on_error=(self.on_error, None),
            search=(self.search, "breadth"),
            filter=(self.filter, None),
            exclude=(self.exclude, None),
            filter_dirs=(self.filter_dirs, None),
            exclude_dirs=(self.exclude_dirs, None),
            max_depth=(self.max_depth, None),
            filter_glob=(self.filter_glob, None),
            exclude_glob=(self.exclude_glob, None),
        )

    def _iter_walk(
        self,
        fs,
        path,
        namespaces=None,
    ):
        """Get the walk generator."""
        if self.search == "breadth":
            return self._walk_breadth(fs, path, namespaces=namespaces)
        else:
            return self._walk_depth(fs, path, namespaces=namespaces)

    def _check_open_dir(self, fs, path, info):
        """Check if a directory should be considered in the walk."""
        full_path = combine(path, info.name)
        if self.exclude_dirs is not None and fs.match(self.exclude_dirs, info.name):
            return False
        if self.exclude_glob is not None and fs.match_glob(
            self.exclude_glob, full_path
        ):
            return False
        if self.filter_dirs is not None and not fs.match(self.filter_dirs, info.name):
            return False
        if self.filter_glob is not None and not fs.match_glob(
            self.filter_glob, full_path, accept_prefix=True
        ):
            return False
        return self.check_open_dir(fs, path, info)

    def check_open_dir(self, fs, path, info):
        """Check if a directory should be opened.

        Override to exclude directories from the walk.

        Arguments:
            fs (FS): A filesystem instance.
            path (str): Path to directory.
            info (Info): A resource info object for the directory.

        Returns:
            bool: `True` if the directory should be opened.

        """
        return True

    def _check_scan_dir(self, fs, path, info, depth):
        """Check if a directory contents should be scanned."""
        if self.max_depth is not None and depth >= self.max_depth:
            return False
        return self.check_scan_dir(fs, path, info)

    def check_scan_dir(self, fs, path, info):
        """Check if a directory should be scanned.

        Override to omit scanning of certain directories. If a directory
        is omitted, it will appear in the walk but its files and
        sub-directories will not.

        Arguments:
            fs (FS): A filesystem instance.
            path (str): Path to directory.
            info (Info): A resource info object for the directory.

        Returns:
            bool: `True` if the directory should be scanned.

        """
        return True

    def _check_file(self, fs, dir_path, info):
        """Check if a filename should be included."""
        # Weird check required for backwards compatibility,
        # when _check_file did not exist.
        if Walker._check_file == type(self)._check_file:
            if self.exclude is not None and fs.match(self.exclude, info.name):
                return False
            if self.exclude_glob is not None and fs.match_glob(
                self.exclude_glob, dir_path + "/" + info.name
            ):
                return False
            if self.filter is not None and not fs.match(self.filter, info.name):
                return False
            if self.filter_glob is not None and not fs.match_glob(
                self.filter_glob, dir_path + "/" + info.name, accept_prefix=True
            ):
                return False
        return self.check_file(fs, info)

    def check_file(self, fs, info):
        """Check if a filename should be included.

        Override to exclude files from the walk.

        Arguments:
            fs (FS): A filesystem instance.
            info (Info): A resource info object.

        Returns:
            bool: `True` if the file should be included.

        """
        return True

    def _scan(
        self,
        fs,
        dir_path,
        namespaces=None,
    ):
        """Get an iterator of `Info` objects for a directory path.

        Arguments:
            fs (FS): A filesystem instance.
            dir_path (str): A path to a directory on the filesystem.
            namespaces (list): A list of additional namespaces to
                include in the `Info` objects.

        Returns:
            ~collections.Iterator: iterator of `Info` objects for
            resources within the given path.

        """
        try:
            for info in fs.scandir(dir_path, namespaces=namespaces):
                yield info
        except FSError as error:
            if not self.on_error(dir_path, error):
                raise

    def walk(
        self,
        fs,
        path="/",
        namespaces=None,
    ):
        """Walk the directory structure of a filesystem.

        Arguments:
            fs (FS): A filesystem instance.
            path (str): A path to a directory on the filesystem.
            namespaces (list): A list of additional namespaces
                to add to the `Info` objects.

        Returns:
            collections.Iterator: an iterator of `~fs.walk.Step` instances.

        The return value is an iterator of ``(<path>, <dirs>, <files>)``
        named tuples,  where ``<path>`` is an absolute path to a
        directory, and ``<dirs>`` and ``<files>`` are a list of
        `~fs.info.Info` objects for directories and files in ``<path>``.
        """
        _path = abspath(normpath(path))
        dir_info = defaultdict(list)
        _walk = self._iter_walk(fs, _path, namespaces=namespaces)
        for dir_path, info in _walk:
            if info is None:
                dirs = []
                files = []
                for _info in dir_info[dir_path]:
                    (dirs if _info.is_dir else files).append(_info)
                yield Step(dir_path, dirs, files)
                del dir_info[dir_path]
            else:
                dir_info[dir_path].append(info)

    def files(self, fs, path="/"):
        """Walk a filesystem, yielding absolute paths to files.

        Arguments:
            fs (FS): A filesystem instance.
            path (str): A path to a directory on the filesystem.

        Yields:
            str: absolute path to files on the filesystem found
            recursively within the given directory.

        """
        _combine = combine
        for _path, info in self._iter_walk(fs, path=path):
            if info is not None and not info.is_dir:
                yield _combine(_path, info.name)

    def dirs(self, fs, path="/"):
        """Walk a filesystem, yielding absolute paths to directories.

        Arguments:
            fs (FS): A filesystem instance.
            path (str): A path to a directory on the filesystem.

        Yields:
            str: absolute path to directories on the filesystem found
            recursively within the given directory.

        """
        _combine = combine
        for _path, info in self._iter_walk(fs, path=path):
            if info is not None and info.is_dir:
                yield _combine(_path, info.name)

    def info(
        self,
        fs,
        path="/",
        namespaces=None,
    ):
        """Walk a filesystem, yielding tuples of ``(<path>, <info>)``.

        Arguments:
            fs (FS): A filesystem instance.
            path (str): A path to a directory on the filesystem.
            namespaces (list): A list of additional namespaces
                to add to the `Info` objects.

        Yields:
            (str, Info): a tuple of ``(<absolute path>, <resource info>)``.

        """
        _combine = combine
        _walk = self._iter_walk(fs, path=path, namespaces=namespaces)
        for _path, info in _walk:
            if info is not None:
                yield _combine(_path, info.name), info

    def _walk_breadth(
        self,
        fs,
        path,
        namespaces=None,
    ):
        """Walk files using a *breadth first* search."""
        queue = deque([path])
        push = queue.appendleft
        pop = queue.pop

        _combine = combine
        _scan = self._scan
        _calculate_depth = self._calculate_depth
        _check_open_dir = self._check_open_dir
        _check_scan_dir = self._check_scan_dir
        _check_file = self._check_file

        depth = _calculate_depth(path)

        while queue:
            dir_path = pop()
            for info in _scan(fs, dir_path, namespaces=namespaces):
                if info.is_dir:
                    _depth = _calculate_depth(dir_path) - depth + 1
                    if _check_open_dir(fs, dir_path, info):
                        yield dir_path, info  # Opened a directory
                        if _check_scan_dir(fs, dir_path, info, _depth):
                            push(_combine(dir_path, info.name))
                else:
                    if _check_file(fs, dir_path, info):
                        yield dir_path, info  # Found a file
            yield dir_path, None  # End of directory

    def _walk_depth(
        self,
        fs,
        path,
        namespaces=None,
    ):
        """Walk files using a *depth first* search."""
        # No recursion!

        _combine = combine
        _scan = self._scan
        _calculate_depth = self._calculate_depth
        _check_open_dir = self._check_open_dir
        _check_scan_dir = self._check_scan_dir
        _check_file = self._check_file
        depth = _calculate_depth(path)

        stack = [(path, _scan(fs, path, namespaces=namespaces), None)]

        push = stack.append

        while stack:
            dir_path, iter_files, parent = stack[-1]
            info = next(iter_files, None)
            if info is None:
                if parent is not None:
                    yield parent
                yield dir_path, None
                del stack[-1]
            elif info.is_dir:
                _depth = _calculate_depth(dir_path) - depth + 1
                if _check_open_dir(fs, dir_path, info):
                    if _check_scan_dir(fs, dir_path, info, _depth):
                        _path = _combine(dir_path, info.name)
                        push(
                            (
                                _path,
                                _scan(fs, _path, namespaces=namespaces),
                                (dir_path, info),
                            )
                        )
                    else:
                        yield dir_path, info
            else:
                if _check_file(fs, dir_path, info):
                    yield dir_path, info


class BoundWalker:
    """A class that binds a `Walker` instance to a `FS` instance.

    You will typically not need to create instances of this class
    explicitly. Filesystems have a `~FS.walk` property which returns a
    `BoundWalker` object.

    A `BoundWalker` is callable. Calling it is an alias for the
    `~fs.walk.BoundWalker.walk` method.
    """

    def __init__(self, fs, walker_class=Walker):
        """Create a new walker bound to the given filesystem.

        Arguments:
            fs (FS): A filesystem instance.
            walker_class (type): A `~fs.walk.WalkerBase`
                sub-class. The default uses `~fs.walk.Walker`.

        """
        self.fs = fs
        self.walker_class = walker_class

    def __repr__(self):
        """Return a string representation of the bound walker."""
        return "BoundWalker({!r})".format(self.fs)

    def _make_walker(self, *args, **kwargs):
        """Create a walker instance."""
        walker = self.walker_class(*args, **kwargs)
        return walker

    def walk(self, path="/", namespaces=None, **kwargs):
        """Walk the directory structure of a filesystem.

        Arguments:
            path (str):
            namespaces (list): A list of namespaces to include
                in the resource information, e.g. ``['basic', 'access']``
                (defaults to ``['basic']``).

        Keyword Arguments:
            ignore_errors (bool): If `True`, any errors reading a
                directory will be ignored, otherwise exceptions will be
                raised.
            on_error (callable): If ``ignore_errors`` is `False`, then
                this callable will be invoked with a path and the exception
                object. It should return `True` to ignore the error, or
                `False` to re-raise it.
            search (str): If ``'breadth'`` then the directory will be
                walked *top down*. Set to ``'depth'`` to walk *bottom up*.
            filter (list): If supplied, this parameter should be a list
                of file name patterns, e.g. ``['*.py']``. Files will only be
                returned if the final component matches one of the
                patterns.
            exclude (list): If supplied, this parameter should be
                a list of filename patterns, e.g. ``['~*', '.*']``. Files matching
                any of these patterns will be removed from the walk.
            filter_dirs (list): A list of patterns that will be used
                to match directories paths. The walk will only open directories
                that match at least one of these patterns.
            exclude_dirs (list): A list of patterns that will be used
                to filter out directories from the walk, e.g. ``['*.svn',
                '*.git']``.
            max_depth (int): Maximum directory depth to walk.

        Returns:
            ~collections.Iterator: an iterator of ``(<path>, <dirs>, <files>)``
            named tuples,  where ``<path>`` is an absolute path to a
            directory, and ``<dirs>`` and ``<files>`` are a list of
            `~fs.info.Info` objects for directories and files in ``<path>``.

        This method invokes `Walker.walk` with bound `FS` object.

        """
        walker = self._make_walker(**kwargs)
        return walker.walk(self.fs, path=path, namespaces=namespaces)

    __call__ = walk

    def files(self, path="/", **kwargs):
        """Walk a filesystem, yielding absolute paths to files.

        Arguments:
            path (str): A path to a directory.

        Keyword Arguments:
            ignore_errors (bool): If `True`, any errors reading a
                directory will be ignored, otherwise exceptions will be
                raised.
            on_error (callable): If ``ignore_errors`` is `False`, then
                this callable will be invoked with a path and the exception
                object. It should return `True` to ignore the error, or
                `False` to re-raise it.
            search (str): If ``'breadth'`` then the directory will be
                walked *top down*. Set to ``'depth'`` to walk *bottom up*.
            filter (list): If supplied, this parameter should be a list
                of file name patterns, e.g. ``['*.py']``. Files will only be
                returned if the final component matches one of the
                patterns.
            exclude (list): If supplied, this parameter should be
                a list of filename patterns, e.g. ``['~*', '.*']``. Files matching
                any of these patterns will be removed from the walk.
            filter_dirs (list): A list of patterns that will be used
                to match directories paths. The walk will only open directories
                that match at least one of these patterns.
            exclude_dirs (list): A list of patterns that will be used
                to filter out directories from the walk, e.g. ``['*.svn',
                '*.git']``.
            max_depth (int): Maximum directory depth to walk.

        Returns:
            ~collections.Iterator: An iterator over file paths (absolute
            from the filesystem root).

        This method invokes `Walker.files` with the bound `FS` object.

        """
        walker = self._make_walker(**kwargs)
        return walker.files(self.fs, path=path)

    def dirs(self, path="/", **kwargs):
        """Walk a filesystem, yielding absolute paths to directories.

        Arguments:
            path (str): A path to a directory.

        Keyword Arguments:
            ignore_errors (bool): If `True`, any errors reading a
                directory will be ignored, otherwise exceptions will be
                raised.
            on_error (callable): If ``ignore_errors`` is `False`, then
                this callable will be invoked with a path and the exception
                object. It should return `True` to ignore the error, or
                `False` to re-raise it.
            search (str): If ``'breadth'`` then the directory will be
                walked *top down*. Set to ``'depth'`` to walk *bottom up*.
            filter_dirs (list): A list of patterns that will be used
                to match directories paths. The walk will only open directories
                that match at least one of these patterns.
            exclude_dirs (list): A list of patterns that will be used
                to filter out directories from the walk, e.g. ``['*.svn',
                '*.git']``.
            max_depth (int): Maximum directory depth to walk.

        Returns:
            ~collections.Iterator: an iterator over directory paths
            (absolute from the filesystem root).

        This method invokes `Walker.dirs` with the bound `FS` object.

        """
        walker = self._make_walker(**kwargs)
        return walker.dirs(self.fs, path=path)

    def info(self, path="/", namespaces=None, **kwargs):
        """Walk a filesystem, yielding path and `Info` of resources.

        Arguments:
            path (str): A path to a directory.
            namespaces (list): A list of namespaces to include
                in the resource information, e.g. ``['basic', 'access']``
                (defaults to ``['basic']``).

        Keyword Arguments:
            ignore_errors (bool): If `True`, any errors reading a
                directory will be ignored, otherwise exceptions will be
                raised.
            on_error (callable): If ``ignore_errors`` is `False`, then
                this callable will be invoked with a path and the exception
                object. It should return `True` to ignore the error, or
                `False` to re-raise it.
            search (str): If ``'breadth'`` then the directory will be
                walked *top down*. Set to ``'depth'`` to walk *bottom up*.
            filter (list): If supplied, this parameter should be a list
                of file name patterns, e.g. ``['*.py']``. Files will only be
                returned if the final component matches one of the
                patterns.
            exclude (list): If supplied, this parameter should be
                a list of filename patterns, e.g. ``['~*', '.*']``. Files matching
                any of these patterns will be removed from the walk.
            filter_dirs (list): A list of patterns that will be used
                to match directories paths. The walk will only open directories
                that match at least one of these patterns.
            exclude_dirs (list): A list of patterns that will be used
                to filter out directories from the walk, e.g. ``['*.svn',
                '*.git']``.
            max_depth (int): Maximum directory depth to walk.

        Returns:
            ~collections.Iterable: an iterable yielding tuples of
            ``(<absolute path>, <resource info>)``.

        This method invokes `Walker.info` with the bound `FS` object.

        """
        walker = self._make_walker(**kwargs)
        return walker.info(self.fs, path=path, namespaces=namespaces)


# ============================================================================
# Info Class
# ============================================================================


class Info:
    """Container for :ref:`info`.

    Resource information is returned by the following methods:

         * `~fs.base.FS.getinfo`
         * `~fs.base.FS.scandir`
         * `~fs.base.FS.filterdir`

    Arguments:
        raw_info (dict): A dict containing resource info.
        to_datetime (callable): A callable that converts an
            epoch time to a datetime object. The default uses
            `~fs.time.epoch_to_datetime`.

    """

    __slots__ = ["raw", "_to_datetime", "namespaces"]

    def __init__(self, raw_info, to_datetime=epoch_to_datetime):
        """Create a resource info object from a raw info dict."""
        self.raw = raw_info
        self._to_datetime = to_datetime
        self.namespaces = frozenset(self.raw.keys())

    def __str__(self):
        """Return a string representation of the resource info."""
        if self.is_dir:
            return "<dir '{}'>".format(self.name)
        else:
            return "<file '{}'>".format(self.name)

    __repr__ = __str__

    def __eq__(self, other):
        """Check if two resource info objects are equal."""
        return self.raw == getattr(other, "raw", None)

    def _make_datetime(self, t):
        if t is not None:
            return self._to_datetime(t)
        else:
            return None

    def get(self, namespace, key, default=None):
        """Get a raw info value.

        Arguments:
            namespace (str): A namespace identifier.
            key (str): A key within the namespace.
            default (object): A default value to return
                if either the namespace or the key within the namespace
                is not found.
        """
        try:
            return self.raw[namespace].get(key, default)  # type: ignore
        except KeyError:
            return default

    def _require_namespace(self, namespace):
        """Check if the given namespace is present in the info.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the given namespace is not
                present in the info.

        """
        if namespace not in self.raw:
            raise MissingInfoNamespace(namespace)

    def is_writeable(self, namespace, key):
        """Check if a given key in a namespace is writable.

        When creating an `Info` object, you can add a ``_write`` key to
        each raw namespace that lists which keys are writable or not.

        In general, this means they are compatible with the `setinfo`
        function of filesystem objects.

        Arguments:
            namespace (str): A namespace identifier.
            key (str): A key within the namespace.

        Returns:
            bool: `True` if the key can be modified, `False` otherwise.
        """
        _writeable = self.get(namespace, "_write", ())
        return key in _writeable

    def has_namespace(self, namespace):
        """Check if the resource info contains a given namespace.

        Arguments:
            namespace (str): A namespace identifier.

        Returns:
            bool: `True` if the namespace was found, `False` otherwise.

        """
        return namespace in self.raw

    def copy(self, to_datetime=None):
        """Create a copy of this resource info object."""
        return Info(deepcopy(self.raw), to_datetime=to_datetime or self._to_datetime)

    def make_path(self, dir_path):
        """Make a path by joining ``dir_path`` with the resource name.

        Arguments:
            dir_path (str): A path to a directory.

        Returns:
            str: A path to the resource.

        """
        return join(dir_path, self.name)

    @property
    def name(self):
        """`str`: the resource name."""
        return str(self.get("basic", "name"))

    @property
    def suffix(self):
        """`str`: the last component of the name (with dot).

        In case there is no suffix, an empty string is returned.
        """
        name = self.get("basic", "name")
        if name.startswith(".") and name.count(".") == 1:
            return ""
        basename, dot, ext = name.rpartition(".")
        return "." + ext if dot else ""

    @property
    def suffixes(self):
        """`List`: a list of any suffixes in the name."""
        name = self.get("basic", "name")
        if name.startswith(".") and name.count(".") == 1:
            return []
        return ["." + suffix for suffix in name.split(".")[1:]]

    @property
    def stem(self):
        """`str`: the name minus any suffixes."""
        name = self.get("basic", "name")
        if name.startswith("."):
            return name
        return name.split(".")[0]

    @property
    def is_dir(self):
        """`bool`: `True` if the resource references a directory."""
        return bool(self.get("basic", "is_dir"))

    @property
    def is_file(self):
        """`bool`: `True` if the resource references a file."""
        return not bool(self.get("basic", "is_dir"))

    @property
    def is_link(self):
        """`bool`: `True` if the resource is a symlink."""
        self._require_namespace("link")
        return self.get("link", "target", None) is not None

    @property
    def type(self):
        """`~fs.enums.ResourceType`: the type of the resource.

        Requires the ``"details"`` namespace.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the 'details'
                namespace is not in the Info.
        """
        self._require_namespace("details")
        return ResourceType(self.get("details", "type", 0))

    @property
    def accessed(self):
        """`~datetime.datetime`: the resource last access time, or `None`.

        Requires the ``"details"`` namespace.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the ``"details"``
                namespace is not in the Info.
        """
        self._require_namespace("details")
        _time = self._make_datetime(self.get("details", "accessed"))
        return _time

    @property
    def modified(self):
        """`~datetime.datetime`: the resource last modification time, or `None`.

        Requires the ``"details"`` namespace.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the ``"details"``
                namespace is not in the Info.
        """
        self._require_namespace("details")
        _time = self._make_datetime(self.get("details", "modified"))
        return _time

    @property
    def created(self):
        """`~datetime.datetime`: the resource creation time, or `None`.

        Requires the ``"details"`` namespace.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the ``"details"``
                namespace is not in the Info.
        """
        self._require_namespace("details")
        _time = self._make_datetime(self.get("details", "created"))
        return _time

    @property
    def metadata_changed(self):
        """`~datetime.datetime`: the resource metadata change time, or `None`.

        Requires the ``"details"`` namespace.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the ``"details"``
                namespace is not in the Info.
        """
        self._require_namespace("details")
        _time = self._make_datetime(self.get("details", "metadata_changed"))
        return _time

    @property
    def permissions(self):
        """Permissions return object that requires to be implemented."""
        raise NotImplementedError

    @property
    def size(self):
        """`int`: the size of the resource, in bytes.

        Requires the ``"details"`` namespace.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the ``"details"``
                namespace is not in the Info.
        """
        self._require_namespace("details")
        return int(self.get("details", "size"))

    @property
    def user(self):
        """`str`: the owner of the resource, or `None`.

        Requires the ``"access"`` namespace.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the ``"access"``
                namespace is not in the Info.
        """
        self._require_namespace("access")
        return self.get("access", "user")

    @property
    def uid(self):
        """`int`: the user id of the resource, or `None`.

        Requires the ``"access"`` namespace.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the ``"access"``
                namespace is not in the Info.

        """
        self._require_namespace("access")
        return self.get("access", "uid")

    @property
    def group(self):
        """`str`: the group of the resource owner, or `None`.

        Requires the ``"access"`` namespace.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the ``"access"``
                namespace is not in the Info.
        """
        self._require_namespace("access")
        return self.get("access", "group")

    @property
    def gid(self):
        """`int`: the group id of the resource, or `None`.

        Requires the ``"access"`` namespace.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the ``"access"``
                namespace is not in the Info.
        """
        self._require_namespace("access")
        return self.get("access", "gid")

    @property
    def target(self):
        """Return the target of a symlink, or `None`.

        Requires the ``"link"`` namespace.

        Raises:
            ~fs.errors.MissingInfoNamespace: if the ``"link"``
                namespace is not in the Info.
        """
        self._require_namespace("link")
        return self.get("link", "target")


# ============================================================================
# FS Base Class
# ============================================================================


class FS:
    """Base filesystem class.

    This is a minimal base class that provides the interface expected by
    the PyFilesystem ecosystem. It provides default implementations that
    raise NotImplementedError for methods not implemented by subclasses.
    """

    _meta = {}

    @property
    def walk(self):
        """`~fs.walk.BoundWalker`: a walker bound to this filesystem."""
        raise NotImplementedError("walk must be implemented by the filesystem subclass")

    def __init__(self):
        """Initialize filesystem."""
        pass

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
        """Open a file.

        :param path: Path to the file.
        :param mode: File mode.
        :param buffering: Buffering policy.
        :param encoding: Text encoding.
        :param errors: Error handling.
        :param newline: Newline character.
        :param line_buffering: Line buffering.
        :return: File-like object.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def opendir(self, path, factory=None):
        """Open a directory as a filesystem.

        :param path: Path to directory.
        :param factory: Factory function (not used).
        :return: New filesystem instance for the directory.
        """
        # Create a new filesystem instance with the base path set to the
        # directory path
        if hasattr(self, "base_path"):
            # For XRootDPyFS-like filesystems
            new_fs = self.__class__(self.root_url + "/" + path.lstrip("/"))
            return new_fs
        else:
            # Generic fallback
            raise NotImplementedError

    def listdir(
        self,
        path="./",
        wildcard=None,
        full=False,
        absolute=False,
        dirs_only=False,
        files_only=False,
    ):
        """List directory contents.

        :param path: Path to list.
        :param wildcard: Filter pattern.
        :param full: Return full paths.
        :param absolute: Return absolute paths.
        :param dirs_only: Only directories.
        :param files_only: Only files.
        :return: List of entries.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def ilistdir(
        self,
        path="./",
        wildcard=None,
        full=False,
        absolute=False,
        dirs_only=False,
        files_only=False,
    ):
        """Iterate over directory contents.

        :param path: Path to list.
        :param wildcard: Filter pattern.
        :param full: Return full paths.
        :param absolute: Return absolute paths.
        :param dirs_only: Only directories.
        :param files_only: Only files.
        :return: Generator of entries.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def exists(self, path):
        """Check if path exists.

        :param path: Path to check.
        :return: True if exists.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def isfile(self, path):
        """Check if path is a file.

        :param path: Path to check.
        :return: True if file.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def isdir(self, path):
        """Check if path is a directory.

        :param path: Path to check.
        :return: True if directory.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def makedir(
        self,
        path,
        recursive=False,
        allow_recreate=False,
        permissions=None,
        recreate=False,
    ):
        """Make a directory.

        :param path: Path to create.
        :param recursive: Create parent directories.
        :param allow_recreate: Allow if exists.
        :param permissions: Permissions (not used).
        :param recreate: Alias for allow_recreate.
        :return: True on success.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def remove(self, path):
        """Remove a file.

        :param path: Path to remove.
        :return: True on success.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def removedir(self, path, recursive=False, force=False):
        """Remove a directory.

        :param path: Path to remove.
        :param recursive: Remove recursively.
        :param force: Force removal.
        :return: True on success.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def rename(self, src, dst):
        """Rename a file or directory.

        :param src: Source path.
        :param dst: Destination path.
        :return: True on success.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def move(self, src, dst, overwrite=False, **kwargs):
        """Move a file or directory.

        :param src: Source path.
        :param dst: Destination path.
        :param overwrite: Overwrite if exists.
        :return: True on success.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def movedir(self, src, dst, overwrite=False, **kwargs):
        """Move a directory.

        :param src: Source path.
        :param dst: Destination path.
        :param overwrite: Overwrite if exists.
        :return: True on success.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def copy(self, src, dst, overwrite=False):
        """Copy a file.

        :param src: Source path.
        :param dst: Destination path.
        :param overwrite: Overwrite if exists.
        :return: True on success.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def copydir(self, src, dst, overwrite=False, parallel=True):
        """Copy a directory.

        :param src: Source path.
        :param dst: Destination path.
        :param overwrite: Overwrite if exists.
        :param parallel: Use parallel copy.
        :return: True on success.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def getinfo(self, path, namespaces=None):
        """Get file information.

        :param path: Path to get info for.
        :param namespaces: Namespaces to include.
        :return: Info object.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def setinfo(self, path, info):
        """Set file information.

        :param path: Path to set info for.
        :param info: Info to set.
        :return: True on success.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def scandir(
        self,
        path,
        namespaces=None,
        page=None,
    ):
        """Get an iterator of resource info.

        Arguments:
            path (str): A path to a directory on the filesystem.
            namespaces (list): A list of namespaces to include
                in the resource information, e.g. ``['basic', 'access']``.
            page (tuple): May be a tuple of ``(<start>, <end>)``
                indexes to return an iterator of a subset of the resource
                info, or `None` to iterate over the entire directory.
                Paging a directory scan may be necessary for very large
                directories.

        Returns:
            ~collections.abc.Iterator: an iterator of `Info` objects.

        Raises:
            fs.errors.DirectoryExpected: If ``path`` is not a directory.
            fs.errors.ResourceNotFound: If ``path`` does not exist.
        """
        raise NotImplementedError(
            "scandir must be implemented by the filesystem subclass"
        )

    def getpathurl(self, path, allow_none=False, with_querystring=False):
        """Get URL for a path.

        :param path: Path to get URL for.
        :param allow_none: Allow None.
        :param with_querystring: Include query string.
        :return: URL string.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def openbin(self, path, mode="r", buffering=-1, **options):
        """Open file in binary mode.

        :param path: Path to file.
        :param mode: File mode.
        :param buffering: Buffering policy.
        :param options: Additional options.
        :return: File-like object.
        :raises NotImplementedError: Always, must be overridden.
        """
        raise NotImplementedError

    def readtext(self, path, encoding=None, errors=None, newline=None):
        """Read text from a file.

        :param path: Path to file.
        :param encoding: Text encoding.
        :param errors: Error handling.
        :param newline: Newline handling.
        :return: File contents as bytes or string.
        """
        with self.open(path, mode="rb") as f:
            return f.read()

    def writetext(self, path, content, encoding=None, errors=None, newline=None):
        """Write text to a file.

        :param path: Path to file.
        :param content: Content to write (string or bytes).
        :param encoding: Text encoding.
        :param errors: Error handling.
        :param newline: Newline handling.
        :return: Number of bytes written.
        """
        # Convert string to bytes if needed
        if isinstance(content, str):
            content = content.encode(encoding or "utf-8", errors or "strict")
        with self.open(path, mode="wb") as f:
            return f.write(content)
