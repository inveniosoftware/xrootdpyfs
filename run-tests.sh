# This file is part of xrootdpyfs
# Copyright (C) 2015-2020 CERN.
#
# xrootdpyfs is free software; you can redistribute it and/or modify it under
# the terms of the Revised BSD License; see LICENSE file for more details.

pydocstyle xrootdpyfs && \
isort -rc -c -df . && \
sphinx-build -qnNW docs docs/_build/html && \
pytest tests/
