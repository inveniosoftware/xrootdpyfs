import pytest
import uuid
from fs.osfs import OSFS

from configobj import ConfigObj
# base_dir

@pytest.fixture
def test_dir(cfg):
    return cfg['localfs']['base_dir']

@pytest.fixture(scope='session')
def anfs(cfg):
    return OSFS(test_dir(cfg))


# wonder if I can have two Test_x-classes w/o py.test complaining.
class Test_Stuff():
    def test_filecreation(self, anfs, rnd_fname):
        fname = rnd_fname
        # get number of files in directory
        val_before = len(anfs.listdir())
        # create a file
        f = anfs.open(fname, mode='w')
        f.close()
        assert len(anfs.listdir()) == val_before+1

        anfs.remove(fname)
        assert len(anfs.listdir()) == val_before
