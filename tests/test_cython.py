import pytest

import falcon

try:
    import cython
except ImportError:
    cython = None


class TestCythonized(object):

    @pytest.mark.skipif(not cython, reason='Cython not installed')
    def test_imported_from_c_modules(self):
        assert 'falcon/api.py' not in str(falcon.api)
