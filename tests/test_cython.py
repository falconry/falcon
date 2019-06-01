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
        assert 'falcon/api.py' not in str(falcon.api)

    def test_stream_has_private_read(self):
        stream = falcon.util.BufferedStream(io.BytesIO().read, 8)

        if cython:
            assert not hasattr(stream, '_read')
        else:
            assert hasattr(stream, '_read')
