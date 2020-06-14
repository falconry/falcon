import io

import pytest

from falcon.errors import DelimiterError
from falcon.util import BufferedReader


class WouldHang(RuntimeError):
    pass


class GlitchyStream(io.BytesIO):

    def read(self, size=None):
        if size is None or size == -1:
            raise WouldHang('unbounded read()')

        result = super().read(size)
        if not result:
            raise WouldHang('EOF')
        return result


class FragmentedStream(GlitchyStream):
    def read(self, size=None):
        if size is None or size <= 1:
            return super().read(size)

        if size < 8:
            size = 1
        else:
            size = size // 2

        return super().read(size)


TEST_DATA = (
    b'123456789ABCDEF\n' * 64 * 1024 * 64 +
    b'--boundary1234567890--' +
    b'123456789ABCDEF\n' * 64 * 1024 * 63 +
    b'--boundary1234567890--' +
    b'123456789ABCDEF\n' * 64 * 1024 * 62 +
    b'--boundary1234567890--'
)

TEST_BYTES_IO = GlitchyStream(TEST_DATA)


@pytest.fixture()
def buffered_reader():
    def _reader_fixture(chunk_size=None):
        TEST_BYTES_IO.seek(0)
        return BufferedReader(TEST_BYTES_IO.read, len(TEST_DATA), chunk_size)

    yield _reader_fixture


@pytest.fixture()
def shorter_stream():
    TEST_BYTES_IO.seek(0)
    return BufferedReader(TEST_BYTES_IO.read, 1024, 128)


@pytest.fixture()
def fragmented_stream():
    stream = FragmentedStream(TEST_DATA)
    return BufferedReader(stream.read, len(TEST_DATA))


def test_peek(buffered_reader):
    stream = buffered_reader(16)

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
    stream = BufferedReader(source_stream.read, len(source) - 1)

    assert stream.peek(0) == b''
    assert stream.peek(1) == b'H'
    assert stream.peek(2) == b'He'
    assert stream.peek(16) == b'Hello, world!'
    assert stream.peek(32) == b'Hello, world!'

    assert source_stream.read() == b'\n'


def test_bounded_read():
    stream = io.BytesIO(b'Hello, world!')
    buffered = BufferedReader(stream.read, len('Hello, world'))
    buffered.read()

    assert stream.read() == b'!'


@pytest.mark.parametrize('size', [
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
def test_read_from_buffer(buffered_reader, size):
    stream = buffered_reader(64)
    stream.peek(64)

    assert stream.read(size) == TEST_DATA[:size]
    assert stream.read(1) == TEST_DATA[size:size + 1]


def test_read_until_delimiter_size_check(buffered_reader):
    stream = buffered_reader(64)

    with pytest.raises(ValueError):
        stream.read_until(b'')
    with pytest.raises(ValueError):
        stream.read_until(b'B' * 65)


@pytest.mark.parametrize('size', [
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
def test_read_until_with_size(buffered_reader, size):
    stream = buffered_reader(64)
    assert stream.read_until(b'--boundary1234567890--', size) == (
        TEST_DATA[:size])


def test_read_until(buffered_reader):
    stream = buffered_reader()

    assert len(stream.read_until(b'--boundary1234567890--')) == 64 * 1024**2
    stream.read_until(b'123456789ABCDEF\n')
    assert len(stream.read_until(b'--boundary1234567890--')) == 63 * 1024**2
    stream.read_until(b'123456789ABCDEF\n')
    assert len(stream.read_until(b'--boundary1234567890--')) == 62 * 1024**2


@pytest.mark.parametrize('size1,size2', [
    (11003077, 22000721),
    (13372477, 51637898),
])
def test_irregular_large_read_until(buffered_reader, size1, size2):
    stream = buffered_reader()
    delimiter = b'--boundary1234567890--'

    stream.pipe_until(delimiter, consume_delimiter=True)
    stream.pipe_until(delimiter, consume_delimiter=True)

    expected = b'123456789ABCDEF\n' * 64 * 1024 * 62

    assert stream.read_until(delimiter, 1337) == expected[:1337]

    chunk1 = stream.read_until(delimiter, size1)
    assert len(chunk1) == size1

    chunk2 = stream.read_until(delimiter, size2)
    assert len(chunk2) == size2

    remainder = stream.read_until(delimiter, 62 * 1024 * 1024)
    assert chunk1 + chunk2 + remainder == expected[1337:]


@pytest.mark.parametrize('size', [
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
def test_read_until_from_buffer(shorter_stream, size):
    shorter_stream.peek(128)

    assert shorter_stream.read_until(b'\n1', size) == (
        b'123456789ABCDEF'[:size])


def test_read_until_missing_delimiter(shorter_stream):
    class BoundaryMissing(RuntimeError):
        pass

    with pytest.raises(DelimiterError):
        shorter_stream.read_until(b'--boundary1234567890--',
                                  consume_delimiter=True)


def test_consume_delimiter(shorter_stream):
    shorter_stream.peek()
    shorter_stream.read(113)

    assert shorter_stream.peek(1) == b'2'

    chunk = shorter_stream.read_until(b'1', 15, consume_delimiter=True)
    assert chunk == b'23456789ABCDEF\n'

    assert shorter_stream.read_until(b'ABCDE', 4) == b'2345'


@pytest.mark.parametrize('chunk_size', list(range(46, 63)))
def test_read_until_shared_boundary(chunk_size):
    source = b'-boundary-like-' * 4 + b'--some junk--\n' + b'\n' * 1024
    source_stream = io.BytesIO(source)
    stream = BufferedReader(source_stream.read, len(source), chunk_size)
    assert stream.read_until(b'-boundary-like---') == b'-boundary-like-' * 3
    assert stream.peek(17) == b'-boundary-like---'


def test_pipe(shorter_stream):
    output = io.BytesIO()
    shorter_stream.pipe(output)
    assert len(output.getvalue()) == 1024


def test_pipe_until(buffered_reader):
    stream = buffered_reader(2 ** 16)

    output = io.BytesIO()
    stream.pipe_until(b'--boundary1234567890--', output)
    assert len(output.getvalue()) == 64 * 1024**2


def test_pipe_until_without_destination(buffered_reader):
    stream = buffered_reader(2 ** 16)
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

    stream = BufferedReader(io.BytesIO(source).read, len(source))
    assert stream.readline() == b'Hello, world!\n'
    assert stream.readline() == b'A line.\n'
    assert stream.readline() == b'\n'
    assert stream.readline() == b'A longer line... \n'
    assert stream.readline() == b'SPAM SPAM SPAM SPAM SPAM SPAM SPAM \n'
    assert stream.readline() == b'\n'
    assert stream.readline() == b''
    assert stream.readline() == b''


def test_readline_with_size():
    source = (
        b'Hello, world! This is a short village name in Wales.\n'
        b'Llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch')

    stream = BufferedReader(io.BytesIO(source).read, len(source))
    assert stream.readline(37) == b'Hello, world! This is a short village'
    assert stream.readline(37) == b' name in Wales.\n'
    assert stream.readline(8) == b'Llanfair'
    assert stream.readline(16) == b'pwllgwyngyllgoge'
    assert stream.readline(64) == b'rychwyrndrobwllllantysiliogogogoch'


def test_readlines(shorter_stream):
    assert shorter_stream.readlines() == [b'123456789ABCDEF\n'] * 64


@pytest.mark.parametrize('chunk_size', [
    8,
    16,
    256,
    1024,
    2 ** 16,
])
def test_readlines_hint(buffered_reader, chunk_size):
    stream = buffered_reader(chunk_size)
    assert stream.readlines(100) == [b'123456789ABCDEF\n'] * 7
    assert stream.readlines(64) == [b'123456789ABCDEF\n'] * 4
    assert stream.readlines(16) == [b'123456789ABCDEF\n']


def test_duck_compatibility_with_io_base(shorter_stream):
    assert shorter_stream.readable()
    assert not shorter_stream.seekable()
    assert not shorter_stream.writeable()


def test_fragmented_reads(fragmented_stream):
    b = io.BytesIO()
    fragmented_stream.pipe_until(b'--boundary1234567890--', b)
    assert fragmented_stream.read(2) == b'--'

    fragmented_stream.pipe_until(b'--boundary1234567890--')
    assert fragmented_stream.read(3) == b'--b'

    fragmented_stream.pipe_until(b'--boundary1234567890--')
    assert fragmented_stream.read(7) == b'--bound'

    fragmented_stream.exhaust()
    assert fragmented_stream.read(4) == b''
    assert fragmented_stream.read() == b''
