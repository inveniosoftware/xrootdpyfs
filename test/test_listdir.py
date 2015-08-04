import pytest
from xrootdfs import XRootDFS

from configobj import ConfigObj
cfg = ConfigObj('test/conf.cfg')['xrootd']

@pytest.fixture
def get_fs():
    return XRootDFS(cfg['address'], cfg['home_dir'])

class Test_Listdir():

    # test if all returned elements are unicode-encoded
    def test_encoding(self, get_fs):
        xfs = get_fs
        res = xfs.listdir()
        for e in res:
            assert isinstance(e, unicode) == True
