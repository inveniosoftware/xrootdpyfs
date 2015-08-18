# -*- coding: utf-8 -*-
#
# This file is part of xrootdfs
# Copyright (C) 2015 CERN.
#
# xrootdfs is free software; you can redistribute it and/or modify it under the
# terms of the Revised BSD License; see LICENSE file for more details.

"""."""

import fs.filelike
from XRootD.client import File as XFile


class XRootDFile(fs.filelike.FileLikeBase):

    """."""

    def __init__(self, path, bufsize=1024 * 64, mode='r'):
        """."""
        super(XRootDFile, self).__init__(bufsize)
        # set .__file to empty xrootd.client.File-object.
        self.__file = XFile()

        status, response = self.__file.open(path, mode=mode)
        # todo: raise appropriate errors

    def seek(self, offset, whence=0):
        """."""
        self._ifp = offset

    def read(self, size=0, offset=None, timeout=0, callback=None):
        """."""
        if offset is None:
            offset = self._ifp
        return self._file.read(offset, size, timeout, callback)

    def tell():
        """."""
        pass

    def truncate(size=None):
        """."""
        pass

    def write(string):
        """."""
        pass
