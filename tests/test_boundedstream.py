import io

import pytest

from falcon.stream import BoundedStream
from falcon.util.deprecation import DeprecatedWarning


@pytest.fixture
def bounded_stream():
    return BoundedStream(io.BytesIO(), 1024)


def test_not_writable(bounded_stream):
    assert not bounded_stream.writable()

    with pytest.raises(OSError):
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


@pytest.mark.parametrize('method', ['read', 'readline', 'readlines'])
@pytest.mark.parametrize('size', [-2, -100])
def test_read_rejects_invalid_negative_size(method, size):
    raw = io.BytesIO(b'bodytrailing')
    stream = BoundedStream(raw, 4)

    with pytest.raises(ValueError, match='size must be at least -1'):
        getattr(stream, method)(size)

    assert raw.tell() == 0
    assert stream.read() == b'body'
    assert stream.eof
    assert raw.read() == b'trailing'
