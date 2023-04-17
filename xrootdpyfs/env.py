# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""Set global timeout behavior in environment.

.. note::
    XRootD timeout behavior depends on a number of different parameters:

    * **Timeout resolution**: The time interval between timeout detection.
    * **Timeout**: The time to wait for a response to a request (should be
      larger than timeout resolution).
    * **Connection window**: The time interval during which a single new
      connection will be attempted. Subsequent attempts will not append until
      the next window.
    * **Connection retry**: Number of connection windows to try before
      declaring permanent failure.
"""

from os import environ


def set_timeout(value):
    """Default value for the time after which an error is declared.

    This value can be overwritten on case-by-case in
    :py:class:`xrootdpyfs.fs.XRootDPyFS`.

    Sets the environment variable ``XRD_REQUESTTIMEOUT``.
    """
    environ["XRD_REQUESTTIMEOUT"] = str(value)


def set_timeoutresolution(value):
    """Set resolution for the timeout events.

    Ie. timeout events will be processed only every number of seconds.

    Sets the environment variable ``XRD_TIMEOUTRESOLUTION``.
    """
    environ["XRD_TIMEOUTRESOLUTION"] = str(value)


def set_connectionwindow(value):
    """Set time window for the connection establishment.

    A connection failure is declared if the connection is not established
    within the time window. If a connection failure happened earlier then
    another connection attempt will only be made at the beginning of the
    next window.

    Sets the environment variable ```XRD_CONNECTIONWINDOW``.
    """
    environ["XRD_CONNECTIONWINDOW"] = str(value)


def set_connectionretry(value):
    """Number of connection attempts that should be made.

    I.e number of available connection windows before declaring a permanent
    failure.

    Sets the environment variable ``XRD_CONNECTIONRETRY``.
    """
    environ["XRD_CONNECTIONRETRY"] = str(value)
