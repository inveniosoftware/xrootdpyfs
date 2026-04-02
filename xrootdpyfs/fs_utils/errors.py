"""Copied from PyFileSystem2, which is licensed under the MIT License."""

import typing

if typing.TYPE_CHECKING:
    from typing import Optional, Text


class MissingInfoNamespace(AttributeError):
    """An expected namespace is missing."""

    def __init__(self, namespace):  # noqa: D107
        # type: (Text) -> None
        self.namespace = namespace
        msg = "namespace '{}' is required for this attribute"
        super().__init__(msg.format(namespace))

    def __reduce__(self):
        return type(self), (self.namespace,)


class FSError(Exception):
    """Base exception for the `fs` module."""

    default_message = "Unspecified error"

    def __init__(self, msg=None):  # noqa: D107
        # type: (Optional[Text]) -> None
        self._msg = msg or self.default_message
        super().__init__()

    def __str__(self):
        # type: () -> Text
        """Return the error message."""
        msg = self._msg.format(**self.__dict__)
        return msg

    def __repr__(self):
        # type: () -> Text
        msg = self._msg.format(**self.__dict__)
        return "{}({!r})".format(self.__class__.__name__, msg)


class ResourceError(FSError):
    """Base exception class for error associated with a specific resource."""

    default_message = "failed on path {path}"

    def __init__(self, path, exc=None, msg=None):  # noqa: D107
        # type: (Text, Optional[Exception], Optional[Text]) -> None
        self.path = path
        self.exc = exc
        super().__init__(msg=msg)

    def __reduce__(self):
        return type(self), (self.path, self.exc, self._msg)


class ResourceNotFound(ResourceError):
    """Required resource not found."""

    default_message = "resource '{path}' not found"


class DestinationExists(ResourceError):
    """Target destination already exists."""

    default_message = "destination '{path}' exists"


class DirectoryNotEmpty(ResourceError):
    """Attempt to remove a non-empty directory."""

    default_message = "directory '{path}' is not empty"


class ResourceInvalid(ResourceError):
    """Resource has the wrong type."""

    default_message = "resource '{path}' is invalid for this operation"


class PathError(FSError):
    """Base exception for errors to do with a path string."""

    default_message = "path '{path}' is invalid"

    def __init__(self, path, msg=None, exc=None):  # noqa: D107
        # type: (Text, Optional[Text], Optional[Exception]) -> None
        self.path = path
        self.exc = exc
        super().__init__(msg=msg)

    def __reduce__(self):
        return type(self), (self.path, self._msg, self.exc)


class InvalidPath(PathError):
    """Path can't be mapped on to the underlaying filesystem."""

    default_message = "path '{path}' is invalid on this filesystem "


class IllegalBackReference(ValueError):
    """Too many backrefs exist in a path.

    This error will occur if the back references in a path would be
    outside of the root. For example, ``"/foo/../../"``, contains two back
    references which would reference a directory above the root.

    Note:
        This exception is a subclass of `ValueError` as it is not
        strictly speaking an issue with a filesystem or resource.

    """

    def __init__(self, path):  # noqa: D107
        # type: (Text) -> None
        self.path = path
        msg = ("path '{path}' contains back-references outside of filesystem").format(
            path=path
        )
        super().__init__(msg)

    def __reduce__(self):
        return type(self), (self.path,)


class OperationFailed(FSError):
    """A specific operation failed."""

    default_message = "operation failed, {details}"

    def __init__(
        self,
        path=None,  # type: Optional[Text]
        exc=None,  # type: Optional[Exception]
        msg=None,  # type: Optional[Text]
    ):  # noqa: D107
        # type: (...) -> None
        self.path = path
        self.exc = exc
        self.details = "" if exc is None else str(exc)
        self.errno = getattr(exc, "errno", None)
        super(OperationFailed, self).__init__(msg=msg)

    def __reduce__(self):
        return type(self), (self.path, self.exc, self._msg)


class RemoteConnectionError(OperationFailed):
    """Operations encountered remote connection trouble."""

    default_message = "remote connection error"


class Unsupported(OperationFailed):
    """Operation not supported by the filesystem."""

    default_message = "not supported"
