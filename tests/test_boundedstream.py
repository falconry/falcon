import io

import pytest

from falcon.request_helpers import BoundedStream


@pytest.fixture
def bounded_stream():
    return BoundedStream(io.BytesIO(), 1024)


def test_not_writeable(bounded_stream):
    assert not bounded_stream.writeable()

    with pytest.raises(IOError):
        bounded_stream.write(b'something something')
