import io

import pytest

from falcon.util import BufferedStream


TEST_DATA = (
    b'123456789ABCDEF\n' * 64 * 1024 * 64 +
    b'--boundary1234567890--' +
    b'123456789ABCDEF\n' * 64 * 1024 * 63 +
    b'--boundary1234567890--' +
    b'123456789ABCDEF\n' * 64 * 1024 * 62 +
    b'--boundary1234567890--'
)

TEST_BYTES_IO = io.BytesIO(TEST_DATA)


@pytest.fixture()
def buffered_stream():
    def _stream_fixture(chunk_size=None):
        TEST_BYTES_IO.seek(0)
        return BufferedStream(TEST_BYTES_IO.read, len(TEST_DATA), chunk_size)

    yield _stream_fixture


@pytest.fixture()
def shorter_stream():
    TEST_BYTES_IO.seek(0)
    return BufferedStream(TEST_BYTES_IO.read, 1024, 128)


def test_peek(buffered_stream):
    stream = buffered_stream(16)

    assert stream.peek(0) == b''
    assert stream.peek(1) == b'1'
    assert stream.peek(2) == b'12'
    assert stream.peek(16) == b'123456789ABCDEF\n'
    assert stream.peek(17) == b'123456789ABCDEF\n'
    assert stream.peek(32) == b'123456789ABCDEF\n'

    assert stream.read(15) == b'123456789ABCDEF'

    assert stream.peek(0) == b''
    assert stream.peek(1) == b'\n'
    assert stream.peek(2) == b'\n1'
    assert stream.peek(16) == b'\n123456789ABCDEF'
    assert stream.peek(17) == b'\n123456789ABCDEF'
    assert stream.peek(32) == b'\n123456789ABCDEF'


def test_peek_eof():
    source = b'Hello, world!\n'
    source_stream = io.BytesIO(source)
    stream = BufferedStream(source_stream.read, len(source) - 1)

    assert stream.peek(0) == b''
    assert stream.peek(1) == b'H'
    assert stream.peek(2) == b'He'
    assert stream.peek(16) == b'Hello, world!'
    assert stream.peek(32) == b'Hello, world!'

    assert source_stream.read() == b'\n'


def test_bounded_read():
    stream = io.BytesIO(b'Hello, world!')
    buffered = BufferedStream(stream.read, len('Hello, world'))
    buffered.read()

    assert stream.read() == b'!'


@pytest.mark.parametrize('amount', [
    0,
    1,
    2,
    7,
    62,
    63,
    64,
    65,
    126,
    127,
    128,
    129,
    1000,
    10000,
])
def test_read_from_buffer(buffered_stream, amount):
    stream = buffered_stream(64)
    stream.peek(64)

    assert stream.read(amount) == TEST_DATA[:amount]
    assert stream.read(1) == TEST_DATA[amount:amount + 1]


def test_read_until_delimiter_size_check(buffered_stream):
    stream = buffered_stream(64)

    with pytest.raises(ValueError):
        stream.read_until(b'')
    with pytest.raises(ValueError):
        stream.read_until(b'B' * 65)


@pytest.mark.parametrize('amount', [
    0,
    1,
    2,
    7,
    62,
    63,
    64,
    65,
    126,
    127,
    128,
    129,
    1000,
    10000,
])
def test_read_until_with_amount(buffered_stream, amount):
    stream = buffered_stream(64)
    assert stream.read_until(b'--boundary1234567890--', amount) == (
        TEST_DATA[:amount])


def test_read_until(buffered_stream):
    stream = buffered_stream()

    assert len(stream.read_until(b'--boundary1234567890--')) == 64 * 1024**2
    stream.read_until(b'123456789ABCDEF\n')
    assert len(stream.read_until(b'--boundary1234567890--')) == 63 * 1024**2
    stream.read_until(b'123456789ABCDEF\n')
    assert len(stream.read_until(b'--boundary1234567890--')) == 62 * 1024**2


@pytest.mark.parametrize('amount', [
    0,
    1,
    2,
    7,
    62,
    63,
    64,
    65,
    126,
    127,
    128,
    129,
    1000,
])
def test_read_until_from_buffer(shorter_stream, amount):
    shorter_stream.peek(128)

    assert shorter_stream.read_until(b'\n1', amount) == (
        b'123456789ABCDEF'[:amount])


def test_read_until_missing_delimiter(shorter_stream):
    class BoundaryMissing(RuntimeError):
        pass

    with pytest.raises(BoundaryMissing):
        shorter_stream.read_until(b'--boundary1234567890--',
                                  missing_delimiter_error=BoundaryMissing)


@pytest.mark.parametrize('chunk_size', list(range(46, 63)))
def test_read_until_shared_boundary(chunk_size):
    source = b'-boundary-like-' * 4 + b'--some junk--\n' + b'\n' * 1024
    source_stream = io.BytesIO(source)
    stream = BufferedStream(source_stream.read, len(source), chunk_size)
    assert stream.read_until(b'-boundary-like---') == b'-boundary-like-' * 3
    assert stream.peek(17) == b'-boundary-like---'


def test_pipe(shorter_stream):
    output = io.BytesIO()
    shorter_stream.pipe(output)
    assert len(output.getvalue()) == 1024


def test_pipe_until(buffered_stream):
    stream = buffered_stream(2 ** 16)

    output = io.BytesIO()
    stream.pipe_until(b'--boundary1234567890--', output)
    assert len(output.getvalue()) == 64 * 1024**2


def test_pipe_until_without_destination(buffered_stream):
    stream = buffered_stream(2 ** 16)
    stream.pipe_until(b'--boundary1234567890--')
    assert stream.peek(22) == b'--boundary1234567890--'


def test_exhaust(shorter_stream):
    shorter_stream.exhaust()
    assert not shorter_stream.read()


def test_readline():
    source = (
        b'Hello, world!\n'
        b'A line.\n'
        b'\n'
        b'A longer line... \n' +
        b'SPAM ' * 7 + b'\n' +
        b'\n'
    )

    stream = BufferedStream(io.BytesIO(source).read, len(source))
    assert stream.readline() == b'Hello, world!\n'
    assert stream.readline() == b'A line.\n'
    assert stream.readline() == b'\n'
    assert stream.readline() == b'A longer line... \n'
    assert stream.readline() == b'SPAM SPAM SPAM SPAM SPAM SPAM SPAM \n'
    assert stream.readline() == b'\n'
    assert stream.readline() == b''
    assert stream.readline() == b''


def test_readlines(shorter_stream):
    assert shorter_stream.readlines() == [b'123456789ABCDEF\n'] * 64


@pytest.mark.parametrize('chunk_size', [
    8,
    16,
    256,
    1024,
    2 ** 16,
])
def test_readlines_hint(buffered_stream, chunk_size):
    stream = buffered_stream(chunk_size)
    assert stream.readlines(100) == [b'123456789ABCDEF\n'] * 7
    assert stream.readlines(64) == [b'123456789ABCDEF\n'] * 4
    assert stream.readlines(16) == [b'123456789ABCDEF\n']


def test_duck_compatibility_with_io_base(shorter_stream):
    assert shorter_stream.readable()
    assert not shorter_stream.seekable()
    assert not shorter_stream.writeable()
