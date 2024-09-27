import io

import pytest

from falcon.stream import BoundedStream
from falcon.util.deprecation import DeprecatedWarning


@pytest.fixture
def bounded_stream():
    return BoundedStream(io.BytesIO(), 1024)


def test_not_writable(bounded_stream):
    assert not bounded_stream.writable()

    with pytest.raises(IOError):
        bounded_stream.write(b'something something')


def test_exhausted():
    bs = BoundedStream(io.BytesIO(b'foobar'), 6)
    assert not bs.eof
    with pytest.warns(DeprecatedWarning, match='Use `eof` instead'):
        assert not bs.is_exhausted
    assert bs.read() == b'foobar'
    assert bs.eof
    with pytest.warns(DeprecatedWarning, match='Use `eof` instead'):
        assert bs.is_exhausted
