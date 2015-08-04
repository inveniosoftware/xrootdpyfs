from XRootD.client import File as XFile
import fs.filelike

class XRootDFile(fs.filelike.FileLikeBase):

    def __init__(self, path, bufsize=1024*64, mode='r'):

        super(XRootDFile, self).__init__(bufsize)
        # set .__file to empty xrootd.client.File-object.
        self.__file = XFile()

        status, response = self.__file.open(path, mode=mode)
        # todo: raise appropriate errors


    def seek(self, offset, whence=0):
        self._ifp = offset

    def read(self, size=0, offset=None, timeout=0, callback=None):
        if offset==None:
            offset=self._ifp
        return self._file.read(offset, size, timeout, callback)

    def tell():
        pass

    def truncate(size=None):
        pass

    def write(string):
        pass
