"""Copied from PyFileSystem2, which is licensed under the MIT License."""

import typing

from .walk import BoundWalker, Walker

if typing.TYPE_CHECKING:
    from types import TracebackType
    from typing import (
        Dict,
        Optional,
        Text,
        Type,
        Union,
    )

    _F = typing.TypeVar("_F", bound="FS")


class FS(object):
    """Base class for FS objects.

    Copied from PyFileSystem2, which is licensed under the MIT License.
    """

    # This is the "standard" meta namespace.
    _meta = {}  # type: Dict[Text, Union[Text, int, bool, None]]

    # most FS will use default walking algorithms
    walker_class = Walker

    # default to SubFS, used by opendir and should be returned by makedir(s)
    subfs_class = None

    def __init__(self):
        # type: (...) -> None
        """Create a filesystem. See help(type(self)) for accurate signature."""
        self._closed = False

    def __del__(self):
        """Auto-close the filesystem on exit."""
        self.close()

    def __enter__(self):
        # type: (...) -> FS
        """Allow use of filesystem as a context manager."""
        return self

    def __exit__(
        self,
        exc_type,  # type: Optional[Type[BaseException]]
        exc_value,  # type: Optional[BaseException]
        traceback,  # type: Optional[TracebackType]
    ):
        # type: (...) -> None
        """Close filesystem on exit."""
        self.close()

    def close(self):
        # type: () -> None
        """Close the filesystem and release any resources.

        It is important to call this method when you have finished
        working with the filesystem. Some filesystems may not finalize
        changes until they are closed (archives for example). You may
        call this method explicitly (it is safe to call close multiple
        times), or you can use the filesystem as a context manager to
        automatically close.

        Example:
            >>> with OSFS('~/Desktop') as desktop_fs:
            ...    desktop_fs.writetext(
            ...        'note.txt',
            ...        "Don't forget to tape Game of Thrones"
            ...    )

        If you attempt to use a filesystem that has been closed, a
        `~fs.errors.FilesystemClosed` exception will be thrown.

        """
        self._closed = True

    @property
    def walk(self):
        # type: (_F) -> BoundWalker[_F]
        """`~fs.walk.BoundWalker`: a walker bound to this filesystem."""
        return self.walker_class.bind(self)
