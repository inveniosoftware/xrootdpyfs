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

from setuptools import setup


# Get the version string.  Cannot be done with import!
with open(os.path.join('xrootdpyfs', 'version.py'), 'rt') as f:
    version = re.search(
        '__version__\s*=\s*"(?P<version>.*)"\n',
        f.read()
    ).group('version')

tests_require = [
    "mock>=1.3.0",
    "pytest-invenio>=1.4.0"
]

extras_require = {
    "docs": ["Sphinx>=4.2.0"],
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
        "fs>=2.0.10,<3.0"
        'xrootd>=5.0,<6.0',
    ],
    entry_points={
        'fs.opener': [
            'xrootd = xrootdpyfs.opener:XRootDPyOpener',
        ]
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Topic :: Utilities',
    ],
)
