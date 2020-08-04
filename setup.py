# -*- coding: utf-8 -*-
#
# This file is part of xrootdpyfs
# Copyright (C) 2015 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

"""XRootDPyFS is a PyFilesystem interface to XRootD."""

import os
import re
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):

    """Integration of PyTest with setuptools."""

    user_options = [('pytest-args=', 'a', 'Arguments to pass to py.test')]

    def initialize_options(self):
        """Initialize options."""
        TestCommand.initialize_options(self)
        try:
            from ConfigParser import ConfigParser
        except ImportError:
            from configparser import ConfigParser
        config = ConfigParser()
        config.read("pytest.ini")
        self.pytest_args = config.get("pytest", "addopts").split(" ")

    def finalize_options(self):
        """Finalize options."""
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        """Run tests."""
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

# Get the version string.  Cannot be done with import!
with open(os.path.join('xrootdpyfs', 'version.py'), 'rt') as f:
    version = re.search(
        '__version__\s*=\s*"(?P<version>.*)"\n',
        f.read()
    ).group('version')

tests_require = [
    'coverage>=4.0',
    'mock>=1.3.0',
    'isort>=4.2,<5.0',
    'pytest-cov>=2.0.0',
    'pytest-pep8>=1.0.6',
    'pytest>=4.0.0,<5.0.0',
]

extras_require = {
    "tests": tests_require,
}

setup(
    name='xrootdpyfs',
    version=version,
    description=__doc__,
    url='http://github.com/inveniosoftware/xrootdpyfs/',
    license='BSD',
    author='Invenio Collaboration',
    author_email='info@inveniosoftware.org',
    long_description=open('README.rst').read(),
    packages=['xrootdpyfs', ],
    zip_safe=False,
    platforms='any',
    extras_require=extras_require,
    tests_require=tests_require,
    install_requires=[
        'fs>=0.5.4,<2.0',  # latest release is 0.5.4
        'xrootd<5.0.0',
    ],
    cmdclass={'test': PyTest},
    classifiers=[
        'Programming Language :: Python :: 3',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Topic :: Utilities',
    ],
)
