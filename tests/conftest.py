# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

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
    """Fixture data for XrootDFS."""
    path = tempfile.mkdtemp()
    shutil.copytree(join(dirname(__file__), "data"), join(path, "data"))

    def cleanup():
        shutil.rmtree(path)

    request.addfinalizer(cleanup)
    return path
