import os

import pytest

import falcon
from falcon import asgi
from falcon import testing


@pytest.mark.parametrize(
    'body',
    [
        b'',
        b'\x00',
        b'\x00\xff',
        b'catsup',
        b'\xde\xad\xbe\xef' * 512,
        testing.rand_string(1, 2048),
        os.urandom(100 * 2**20),
    ],
    ids=['empty', 'null', 'null-ff', 'normal', 'long', 'random', 'random-large'],
)
@pytest.mark.parametrize('extra_body', [True, False])
@pytest.mark.parametrize('set_content_length', [True, False])
@pytest.mark.slow
def test_read_all(body, extra_body, set_content_length):
    if extra_body and not set_content_length:
        pytest.skip(
            'extra_body ignores set_content_length so we only need to test '
            'one of the parameter permutations'
        )

    expected_body = body if isinstance(body, bytes) else body.encode()

    def stream():
        stream_body = body
        content_length = None

        if extra_body:
            # NOTE(kgriffs): Test emitting more data than expected to the app
            content_length = len(expected_body)
            stream_body += b'\x00' if isinstance(stream_body, bytes) else '~'
        elif set_content_length:
            content_length = len(expected_body)

        return _stream(stream_body, content_length=content_length)

    async def test_iteration():
        s = stream()

        chunks = [chunk async for chunk in s]
        if not (expected_body or extra_body):
            assert not chunks

        assert b''.join(chunks) == expected_body
        assert await s.read() == b''
        assert await s.readall() == b''
        assert not [chunk async for chunk in s]
        assert s.tell() == len(expected_body)
        assert s.eof

    async def test_readall_a():
        s = stream()
        assert await s.readall() == expected_body
        assert await s.read() == b''
        assert await s.readall() == b''
        assert not [chunk async for chunk in s]
        assert s.tell() == len(expected_body)
        assert s.eof

    async def test_readall_b():
        s = stream()
        assert await s.read() == expected_body
        assert await s.readall() == b''
        assert await s.read() == b''
        assert not [chunk async for chunk in s]
        assert s.tell() == len(expected_body)
        assert s.eof

    async def test_readall_c():
        s = stream()
        body = await s.read(1)
        body += await s.read(None)
        assert body == expected_body
        assert s.tell() == len(expected_body)
        assert s.eof

    async def test_readall_d():
        s = stream()
        assert not s.closed

        if expected_body:
            assert not s.eof
        elif set_content_length:
            assert s.eof
        else:
            # NOTE(kgriffs): Stream doesn't know if there is more data
            #   coming or not until the first read.
            assert not s.eof

        assert s.tell() == 0

        assert await s.read(-2) == b''
        assert await s.read(-3) == b''
        assert await s.read(-100) == b''

        assert await s.read(-1) == expected_body
        assert await s.read(-1) == b''
        assert await s.readall() == b''
        assert await s.read() == b''
        assert not [chunk async for chunk in s]

        assert await s.read(-2) == b''

        assert s.tell() == len(expected_body)
        assert s.eof

        assert not s.closed
        s.close()
        assert s.closed

    for t in (
        test_iteration,
        test_readall_a,
        test_readall_b,
        test_readall_c,
        test_readall_d,
    ):
        falcon.async_to_sync(t)


def test_filelike():
    s = asgi.BoundedStream(testing.ASGIRequestEventEmitter())

    for __ in range(2):
        with pytest.raises(OSError):
            s.fileno()

        assert not s.isatty()
        assert s.readable()
        assert not s.seekable()
        assert not s.writable()

        s.close()

    assert s.closed

    # NOTE(kgriffs): Closing an already-closed stream is a noop.
    s.close()
    assert s.closed

    async def test_iteration():
        with pytest.raises(ValueError):
            await s.read()

        with pytest.raises(ValueError):
            await s.readall()

        with pytest.raises(ValueError):
            await s.exhaust()

        with pytest.raises(ValueError):
            async for chunk in s:
                pass

    falcon.async_to_sync(test_iteration)


async def test_iterate_streaming_request():
    events = iter(
        (
            {'type': 'http.request', 'body': b'Hello, ', 'more_body': True},
            {'type': 'http.request', 'body': b'World', 'more_body': True},
            {'type': 'http.request', 'body': b'!\n', 'more_body': True},
            {'type': 'http.request', 'body': b'', 'more_body': False},
            {'type': 'http.disconnect'},
        )
    )

    async def receive():
        event = next(events)
        assert event['type'] != 'http.disconnect', (
            'would hang until the client times out'
        )
        return event

    s = asgi.BoundedStream(receive)

    assert b''.join([chunk async for chunk in s]) == b'Hello, World!\n'


@pytest.mark.parametrize(
    'body',
    [
        b'',
        b'\x00',
        b'\x00\xff',
        b'catsup',
        b'\xde\xad\xbe\xef' * 512,
        testing.rand_string(1, 2048).encode(),
    ],
    ids=['empty', 'null', 'null-ff', 'normal', 'long', 'random'],
)
@pytest.mark.parametrize('chunk_size', [1, 2, 10, 64, 100, 1000, 10000])
def test_read_chunks(body, chunk_size):
    def stream():
        return _stream(body)

    async def test_nonmixed():
        s = stream()

        assert await s.read(0) == b''

        chunks = []

        while not s.eof:
            chunks.append(await s.read(chunk_size))

        assert b''.join(chunks) == body

    async def test_mixed_a():
        s = stream()

        chunks = []

        chunks.append(await s.read(chunk_size))
        chunks.append(await s.read(chunk_size))
        chunks.append(await s.readall())
        chunks.append(await s.read(chunk_size))

        assert b''.join(chunks) == body

    async def test_mixed_b():
        s = stream()

        chunks = []

        chunks.append(await s.read(chunk_size))
        chunks.append(await s.read(-1))

        assert b''.join(chunks) == body

    async def test_mixed_iter():
        s = stream()

        chunks = [await s.read(chunk_size)]
        chunks += [data async for data in s]

        assert b''.join(chunks) == body

    for t in (test_nonmixed, test_mixed_a, test_mixed_b, test_mixed_iter):
        falcon.async_to_sync(t)
        falcon.async_to_sync(t)


def test_exhaust_with_disconnect():
    async def t():
        emitter = testing.ASGIRequestEventEmitter(
            b'123456789' * 2,
            # NOTE(kgriffs): This must be small enough to create several events
            chunk_size=3,
        )
        s = asgi.BoundedStream(emitter)

        assert await s.read(1) == b'1'
        assert await s.read(2) == b'23'
        emitter.disconnect(exhaust_body=False)
        await s.exhaust()
        assert await s.read(1) == b''
        assert await s.read(100) == b''
        assert s.eof

    falcon.async_to_sync(t)


async def test_exhaust():
    emitter = testing.ASGIRequestEventEmitter(b'123456798' * 1024)
    stream = asgi.BoundedStream(emitter)

    assert await stream.read(1) == b'1'
    assert await stream.read(6) == b'234567'
    assert await stream.read(101) == b'98' + b'123456798' * 11

    await stream.exhaust()

    assert await stream.read(1) == b''
    assert await stream.read(6) == b''
    assert await stream.read(101) == b''
    assert stream.eof


def test_iteration_already_started():
    body = testing.rand_string(1, 2048).encode()
    s = _stream(body)

    async def t():
        stream_iter = s.__aiter__()

        chunks = [await stream_iter.__anext__()]

        with pytest.raises(ValueError):
            stream_iter2 = s.__aiter__()
            await stream_iter2.__anext__()

        while True:
            try:
                chunks.append(await stream_iter.__anext__())
            except StopAsyncIteration:
                break

        assert b''.join(chunks) == body

    falcon.async_to_sync(t)


def _stream(body, content_length=None):
    emitter = testing.ASGIRequestEventEmitter(body)
    return asgi.BoundedStream(emitter, content_length=content_length)


_READ_MODES = ['read', 'readall', 'read_chunks', 'iteration', 'exhaust']


async def _limited_stream(body, max_length, preload_first_event):
    emitter = testing.ASGIRequestEventEmitter(body, chunk_size=4)
    first_event = None

    if preload_first_event:
        # NOTE(ericareg): Make sure the first event actually carries data,
        #   like it would normally be the case with a real ASGI server.
        emitter._emit_empty_chunks = False
        first_event = await emitter.emit()

    return asgi.BoundedStream(emitter, first_event=first_event, max_length=max_length)


async def _consume(stream, mode):
    if mode == 'read':
        return await stream.read()
    if mode == 'readall':
        return await stream.readall()
    if mode == 'read_chunks':
        chunks = []
        while chunk := await stream.read(3):
            chunks.append(chunk)
        return b''.join(chunks)
    if mode == 'iteration':
        return b''.join([chunk async for chunk in stream])

    await stream.exhaust()
    return None


@pytest.mark.parametrize('mode', _READ_MODES)
@pytest.mark.parametrize('preload_first_event', [True, False])
@pytest.mark.parametrize('body_length', [0, 1, 9, 10])
async def test_max_length_not_exceeded(mode, preload_first_event, body_length):
    body = os.urandom(body_length)
    stream = await _limited_stream(body, 10, preload_first_event)

    data = await _consume(stream, mode)
    if mode != 'exhaust':
        assert data == body
    assert stream.eof
    assert await stream.read() == b''


@pytest.mark.parametrize('mode', _READ_MODES)
@pytest.mark.parametrize('preload_first_event', [True, False])
@pytest.mark.parametrize('body_length', [11, 12, 1024])
async def test_max_length_exceeded(mode, preload_first_event, body_length):
    stream = await _limited_stream(os.urandom(body_length), 10, preload_first_event)

    with pytest.raises(falcon.HTTPContentTooLarge) as exc_info:
        await _consume(stream, mode)

    assert exc_info.value.description == 'The request body must not exceed 10 bytes.'

    # NOTE(ericareg): The stream is left at EOF, so it is safe to exhaust it.
    assert stream.eof
    assert await stream.read() == b''
    await stream.exhaust()


async def test_max_length_ignored_with_content_length():
    body = os.urandom(30)
    emitter = testing.ASGIRequestEventEmitter(body, chunk_size=4)
    stream = asgi.BoundedStream(emitter, content_length=30, max_length=10)

    assert await stream.read() == body


async def test_max_length_with_disconnect():
    events = [
        {'type': 'http.request', 'body': b'abc', 'more_body': True},
        {'type': 'http.disconnect'},
    ]

    async def receive():
        return events.pop(0)

    stream = asgi.BoundedStream(receive, max_length=10)

    assert await stream.read() == b'abc'
    assert stream.eof
