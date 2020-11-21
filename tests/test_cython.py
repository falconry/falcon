import io

import pytest

import falcon
import falcon.util

from _util import has_cython  # NOQA


class TestCythonized:

    @pytest.mark.skipif(not has_cython, reason='Cython not installed')
    def test_imported_from_c_modules(self):
        assert 'falcon/app.py' not in str(falcon.app)

    def test_stream_has_private_read(self):
        stream = falcon.util.BufferedReader(io.BytesIO().read, 8)

        if has_cython and falcon.util.IS_64_BITS:
            assert not hasattr(stream, '_read')
        else:
            assert hasattr(stream, '_read')
