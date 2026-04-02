"""Copied from PyFileSystem2, which is licensed under the MIT License."""

import typing
from datetime import datetime, timezone

if typing.TYPE_CHECKING:
    from typing import Optional


@typing.overload
def epoch_to_datetime(t):  # noqa: D103
    # type: (None) -> None
    pass


@typing.overload
def epoch_to_datetime(t):  # noqa: D103
    # type: (int) -> datetime
    pass


def epoch_to_datetime(t):
    # type: (Optional[int]) -> Optional[datetime]
    """Convert epoch time to a UTC datetime."""
    if t is None:
        return None
    return datetime.fromtimestamp(t, tz=timezone.utc)
