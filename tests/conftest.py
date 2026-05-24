# SPDX-FileCopyrightText: 2015-2023 CERN.
# SPDX-License-Identifier: BSD-3-Clause

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
