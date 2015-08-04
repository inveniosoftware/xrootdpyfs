import pytest
import uuid

from XRootD import client

from configobj import ConfigObj

@pytest.fixture
def get_local_fs():
    return OSFS

@pytest.fixture(scope='session')
def cfg():
    return ConfigObj('test/conf.cfg')

@pytest.fixture
def xrootd_client(cfg):
    return client.FileSystem(cfg['xrootd']['address'])

@pytest.fixture
def test_dir(cfg):
    return cfg['xrootd']['home_dir'] + 'test/'

@pytest.fixture
def address(cfg):
    return cfg['xrootd']['address']

@pytest.fixture
def full_path(cfg):
    return address(cfg) + '/' + test_dir(cfg)

# uuid4 strings are on the form "x{8}-x{4}-4x{3}-yx{3}-x{12}"
# where x=[\da-f] (any hexadecimal character)
# and y=[89ab]
@pytest.fixture
def rnd_fname():
    return str(uuid.uuid4())

# removes the '-' from the random filename
@pytest.fixture
def rnd_fname_alphanum():
    return rnd_fname().replace('-', '')

@pytest.fixture
def rnd_fname_short():
    return rnd_fname()[0:8]
