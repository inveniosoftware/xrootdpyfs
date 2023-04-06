# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015-2023 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""Test fixture."""

import shutil
import tempfile
from os.path import dirname, join

import pytest


def mkurl(p):
    """Generate test root URL."""
    return "root://localhost/{0}".format(p)


@pytest.fixture
def tmppath(request):
    """Fixture data for XrootDPyFS."""
    path = tempfile.mkdtemp()
    shutil.copytree(join(dirname(__file__), "data"), join(path, "data"))
    return path
