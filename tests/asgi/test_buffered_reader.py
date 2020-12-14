import io

import pytest

import falcon
from falcon.asgi import reader
from falcon.errors import OperationNotAllowed


async def async_iter(data):
    for item in data:
        yield item


def async_take(source, count=None):
    async def collect():
        result = []
        async for item in source:
            result.append(item)
            if count is not None and count <= len(result):
                return result
        return result

    return falcon.async_to_sync(collect)


async def chop_data(data, min_size=1024, max_size=64 * 1024):
    index = 0
    size = min_size

    while True:
        chunk = data[index:index + size]
        index += size
        if not chunk:
            break
        yield chunk

        size = min(max_size, size + 1)


SOURCE1 = (
    b'Hello',
    b'',
    b'',
    b',',
    b' ',
    b'World!',
    b'\n',
    b'Jus',
    b't tes',
    b'ting some iterato',
    b'r goodne',
    b'',
    b'ss.',
    b'',
    b'\n',
)
DATA1 = b''.join(SOURCE1)

DATA2 = (
    b'123456789ABCDEF\n' * 64 * 1024 * 64 +
    b'--boundary1234567890--' +
    b'123456789ABCDEF\n' * 64 * 1024 * 63 +
    b'--boundary1234567890--' +
    b'123456789ABCDEF\n' * 64 * 1024 * 62 +
    b'--boundary1234567890--'
)
SOURCE2 = tuple(async_take(chop_data(DATA2)))

SOURCE3 = (
    b'1' * 1024 * 1024 + b'333',
    b'2' * 2 * 1024 * 1024 + b'444'
)
DATA3 = b''.join(SOURCE3)


class AsyncSink:

    def __init__(self):
        self._sink = io.BytesIO()

    async def write(self, data):
        self._sink.write(data)

    @property
    def accumulated(self):
        return self._sink.getvalue()


@pytest.fixture()
def reader1():
    return reader.BufferedReader(async_iter(SOURCE1), chunk_size=8)


@pytest.fixture()
def reader2():
    return reader.BufferedReader(async_iter(SOURCE2), chunk_size=2048)


@pytest.fixture()
def reader3():
    return reader.BufferedReader(async_iter(SOURCE3), chunk_size=2048)


def test_basic_aiter(reader1):
    assert async_take(reader1) == [
        b'Hello, World!',
        b'\nJust tes',
        b'ting some iterato',
        b'r goodne',
        b'ss.\n',
    ]


@falcon.runs_sync
async def test_aiter_from_buffer(reader1):
    assert await reader1.read(4) == b'Hell'

    collected = []
    async for chunk in reader1:
        collected.append(chunk)
    assert collected == [
        b'o, World!',
        b'\nJust tes',
        b'ting some iterato',
        b'r goodne',
        b'ss.\n',
    ]


@pytest.mark.parametrize('delimiter,expected', [
    (b'H', []),
    (b'Hello', []),
    (b'o', [b'Hell']),
    (b'ting', [b'Hello, World!', b'\nJust tes']),
    (
        b'404',
        [
            b'Hello, World!',
            b'\nJust tes',
            b'ting some iterato',
            b'r goodne',
            b'ss.\n',
        ],
    ),
])
def test_delimit(reader1, delimiter, expected):
    delimited = reader1.delimit(delimiter)
    assert async_take(delimited) == expected


@falcon.runs_sync
async def test_exhaust(reader1):
    await reader1.exhaust()
    assert await reader1.peek() == b''


@pytest.mark.parametrize('size', [1, 2, 3, 5, 7, 8])
@falcon.runs_sync
async def test_peek(reader1, size):
    assert await reader1.peek(size) == b'Hello, World'[:size]
    assert reader1.tell() == 0


@falcon.runs_sync
async def test_peek_at_eof():
    source = chop_data(b'Hello!')
    stream = reader.BufferedReader(source)
    assert await stream.peek(16) == b'Hello!'


@falcon.runs_sync
async def test_pipe(reader1):
    sink = AsyncSink()
    await reader1.pipe(sink)
    assert sink.accumulated == DATA1
    assert reader1.eof
    assert reader1.tell() == len(sink.accumulated)


@falcon.runs_sync
async def test_pipe_until_delimiter_not_found(reader1):
    sink = AsyncSink()
    await reader1.pipe_until(b'404', sink)
    assert sink.accumulated == DATA1


@pytest.mark.parametrize('sizes,expected', [
    ((0, 1, 2, 5), [b'', b'H', b'el', b'lo, W']),
    (
        (20, 21, 22, 23, 25),
        [
            b'Hello, World!\nJust t',
            b'esting some iterator ',
            b'goodness.\n',
            b'',
            b'',
        ],
    ),
    ((1, 50), [b'H', b'ello, World!\nJust testing some iterator goodness.\n']),
    ((50, 1), [b'Hello, World!\nJust testing some iterator goodness.', b'\n']),
])
@falcon.runs_sync
async def test_read(reader1, sizes, expected):
    results = []
    for size in sizes:
        results.append(await reader1.read(size))

    assert results == expected


@pytest.mark.parametrize('start_size', [1, 16777216])
@falcon.runs_sync
async def test_varying_read_size(reader2, start_size):
    size = start_size
    result = io.BytesIO()

    while True:
        chunk = await reader2.read(size)
        if not chunk:
            break

        result.write(chunk)
        size += 7

    assert result.getvalue() == DATA2


@pytest.mark.parametrize('peek', [0, 1, 8])
@falcon.runs_sync
async def test_readall(reader1, peek):
    if peek:
        await reader1.peek(peek)
    assert await reader1.readall() == DATA1
    assert reader1.eof


@pytest.mark.parametrize('fork', [False, True])
@pytest.mark.parametrize('offset,delimiter,size,expected', [
    (0, b', ', 4, b'Hell'),
    (0, b', ', 5, b'Hello'),
    (0, b', ', -1, b'Hello'),
    (20, b' ', 4, b'esti'),
    (20, b' ', 5, b'estin'),
    (20, b' ', 6, b'esting'),
    (20, b' ', 20, b'esting'),
    (20, b' ', None, b'esting'),
    (0, b'Hell', 13, b''),
    (1, b'ell', 13, b''),
    (2, b'll', 13, b''),
    (3, b'l', 13, b''),
    (2, b'l', 13, b''),
    (0, b'good', 13, b'Hello, World!'),
    (7, b'good', 19, b'World!\nJust testing'),
    (7, b'good', 33, b'World!\nJust testing some iterator'),
    (7, b'good', 34, b'World!\nJust testing some iterator '),
    (7, b'good', 1337, b'World!\nJust testing some iterator '),
    (7, b'good', -1, b'World!\nJust testing some iterator '),
])
@falcon.runs_sync
async def test_read_until(reader1, offset, delimiter, size, expected, fork):
    if offset:
        await reader1.read(offset)

    if fork:
        assert await reader1.delimit(delimiter).read(size) == expected
    else:
        assert await reader1.read_until(delimiter, size) == expected


@falcon.runs_sync
async def test_read_until_with_buffer_edge_case(reader1):
    assert await reader1.read(12) == b'Hello, World'
    assert await reader1.peek(1) == b'!'
    assert await reader1.read_until(b'404', 1) == b'!'
    assert await reader1.read(13) == b'\nJust testing'


def test_placeholder_methods(reader1):
    with pytest.raises(OSError):
        reader1.fileno()

    assert not reader1.isatty()
    assert reader1.readable()
    assert not reader1.seekable()
    assert not reader1.writable()


@falcon.runs_sync
async def test_iteration_started(reader1):
    async for chunk in reader1:
        with pytest.raises(OperationNotAllowed):
            async for nested in reader1:
                pass


@falcon.runs_sync
async def test_invalid_delimiter_length(reader1):
    with pytest.raises(ValueError):
        await reader1.read_until(b'')

    with pytest.raises(ValueError):
        await reader1.pipe_until(b'')

    with pytest.raises(ValueError):
        await reader1.delimit(b'').read()


@pytest.mark.parametrize('size1,size2', [
    (11003077, 22000721),
    (13372477, 51637898),
])
@falcon.runs_sync
async def test_irregular_large_read_until(reader2, size1, size2):
    delimiter = b'--boundary1234567890--'

    await reader2.pipe_until(delimiter, consume_delimiter=True)
    await reader2.pipe_until(delimiter, consume_delimiter=True)

    expected = b'123456789ABCDEF\n' * 64 * 1024 * 62

    assert await reader2.read_until(delimiter, 1337) == expected[:1337]

    chunk1 = await reader2.read_until(delimiter, size1)
    assert len(chunk1) == size1

    chunk2 = await reader2.read_until(delimiter, size2)
    assert len(chunk2) == size2

    remainder = await reader2.read_until(delimiter, 62 * 1024 * 1024)
    assert chunk1 + chunk2 + remainder == expected[1337:]


@falcon.runs_sync
@pytest.mark.parametrize('chunk_size', list(range(46, 63)))
async def test_read_until_shared_boundary(chunk_size):
    source = chop_data(
        b'-boundary-like-' * 4 + b'--some junk--\n' + b'\n' * 1024,
        min_size=chunk_size,
        max_size=chunk_size)
    stream = reader.BufferedReader(source, chunk_size)
    assert await stream.read_until(b'-boundary-like---') == (
        b'-boundary-like-' * 3)
    assert await stream.peek(17) == b'-boundary-like---'


# NOTE(vytas): This is woefully unoptimized, and this test highlights that.
#   Work in progress.
@falcon.runs_sync
async def test_small_reads(reader3):
    ops = 0
    read = 0
    last = b''
    size = 0

    while True:
        size = max(1, (size + ops) % 1337)
        chunk = await reader3.read(size)
        if not chunk:
            break

        ops += 1
        read += len(chunk)
        last = chunk

    assert ops == 4833
    assert read == len(DATA3)
    assert last.endswith(b'4')


@falcon.runs_sync
async def test_small_reads_with_delimiter(reader3):
    ops = 0
    read = 0
    size = 0

    while True:
        size = max(1, (size + ops) % 1337)
        chunk = await reader3.read_until(b'33', size)
        assert chunk.strip(b'1') == b''
        if not chunk:
            break

        ops += 1
        read += len(chunk)

    assert read == 1024 * 1024
