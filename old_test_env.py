# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""Test of environment variables."""

import os

from xrootdpyfs.env import (
    set_connectionretry,
    set_connectionwindow,
    set_timeout,
    set_timeoutresolution,
)


def test_set_timeout():
    """Test set_timeout."""
    set_timeout(20)
    assert os.environ["XRD_REQUESTTIMEOUT"] == "20"


def test_set_timeoutresolution():
    """Test set_timeoutresolution."""
    set_timeoutresolution(2)
    assert os.environ["XRD_TIMEOUTRESOLUTION"] == "2"


def test_set_connectionretry():
    """Test set_timeoutresolution."""
    set_connectionretry(2)
    assert os.environ["XRD_CONNECTIONRETRY"] == "2"


def test_set_connectionwindow():
    """Test set_timeoutresolution."""
    set_connectionwindow(10)
    assert os.environ["XRD_CONNECTIONWINDOW"] == "10"
