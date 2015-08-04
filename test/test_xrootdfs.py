import pytest
import xrootdfs
from xrootdfs import xrdfile
from XRootD import client
from XRootD.client.flags import OpenFlags

# creates a file in the target dir in the target client
# returns its contents, name
@pytest.fixture
def existing_file(xrootd_client, full_path, test_dir, rnd_fname):
    res = { 'name': rnd_fname, 'path': test_dir }
    with client.File() as f:
        f.open(full_path+rnd_fname, OpenFlags.DELETE)
        f.close()
    return res

@pytest.fixture
def xrdfs(address, test_dir):
    return xrootdfs.XRootDFS(address, test_dir)

class Test_FileBasics():

    def test_openfile(self, existing_file, xrdfs):
        ftest = xrdfs.open(existing_file['name'])
        assert type(ftest) == xrootdfs.XRootDFile

