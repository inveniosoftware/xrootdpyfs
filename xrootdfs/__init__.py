# I guess this is how python projects work?

import fs.base
from XRootD import client as xclient
from XRootD.client.flags import OpenFlags
from xrootdfs.xrdfile import *

class XRootDFS(fs.base.FS):
    def __init__(self, addr, path='/'):
        self.fs = xclient.FileSystem(addr)
        self.base_path = path
        self._addr = addr
        self._url = self.base_path + '/' + self._addr

    def listdir(self, path='./'):
        status, res = self.fs.dirlist(self.base_path + path)
        return [unicode(e.name) for e in res]

    def open(self, path, mode='r', buffering=-1, encoding=None, errors=None,
            newline=None, line_buffering=False, **kwargs):
        # path must be full-on address with the server and everything, yo.
        flags = 0
        if 'r' in mode:
            flags += OpenFlags.READ

        return XRootDFile(self._url + path, flags, mode=0)
