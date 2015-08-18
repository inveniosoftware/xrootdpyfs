# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

pep257 xrootdfs && \
sphinx-build -qnNW docs docs/_build/html && \
python setup.py test && \
sphinx-build -qnNW -b doctest docs docs/_build/doctest
