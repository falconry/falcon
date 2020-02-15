import io

import pytest

import falcon
import falcon.util

try:
    import cython
except ImportError:
    cython = None


class TestCythonized:

    @pytest.mark.skipif(not cython, reason='Cython not installed')
    def test_imported_from_c_modules(self):
        assert 'falcon/app.py' not in str(falcon.app)

    def test_stream_has_private_read(self):
        stream = falcon.util.BufferedReader(io.BytesIO().read, 8)

        if cython and falcon.util.IS_64_BITS:
            assert not hasattr(stream, '_read')
        else:
            assert hasattr(stream, '_read')
