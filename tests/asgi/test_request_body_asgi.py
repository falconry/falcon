import json
import os

import pytest

import falcon
import falcon.asgi
import falcon.request
import falcon.testing as testing

SIZE_1_KB = 1024


@pytest.fixture
def resource():
    return testing.SimpleTestResourceAsync()


@pytest.fixture
def client():
    app = falcon.asgi.App()
    return testing.TestClient(app)


class TestRequestBody:
    def test_empty_body(self, client, resource):
        client.app.add_route('/', resource)
        client.simulate_request(path='/', body='')
        stream = resource.captured_req.stream
        assert stream.tell() == 0

    def test_tiny_body(self, client, resource):
        client.app.add_route('/', resource)
        expected_body = '.'

        headers = {'capture-req-body-bytes': '1'}
        client.simulate_request(path='/', body=expected_body, headers=headers)
        stream = resource.captured_req.stream

        assert resource.captured_req_body == expected_body.encode('utf-8')
        assert stream.tell() == 1

    def test_tiny_body_overflow(self, client, resource):
        client.app.add_route('/', resource)
        expected_body = '.'
        expected_len = len(expected_body)

        # Read too many bytes; shouldn't block
        headers = {'capture-req-body-bytes': str(len(expected_body) + 1)}
        client.simulate_request(path='/', body=expected_body, headers=headers)
        stream = resource.captured_req.stream

        assert resource.captured_req_body == expected_body.encode('utf-8')
        assert stream.tell() == expected_len

    @pytest.mark.parametrize(
        'body_length, content_length',
        [
            (1, 0),
            (2, 1),
            (3, 2),
            (100, None),
            (100, 50),
            (8192, 50),
        ],
    )
    async def test_content_length_smaller_than_body(self, body_length, content_length):
        body_in = os.urandom(body_length)

        scope = testing.create_scope(content_length=content_length)
        req_event_emitter = testing.ASGIRequestEventEmitter(body=body_in)
        req_event_emitter._emit_empty_chunks = False
        first_event = await req_event_emitter.emit()
        req = falcon.asgi.Request(scope, req_event_emitter, first_event=first_event)

        body_out = await req.bounded_stream.read()
        assert body_out == body_in[:content_length]

    def test_read_body(self, client, resource):
        client.app.add_route('/', resource)
        expected_body = testing.rand_string(SIZE_1_KB // 2, SIZE_1_KB)
        expected_len = len(expected_body)

        headers = {
            'Content-Length': str(expected_len),
            'Capture-Req-Body-Bytes': '-1',
        }
        client.simulate_request(path='/', body=expected_body, headers=headers)

        content_len = resource.captured_req.get_header('content-length')
        assert content_len == str(expected_len)

        stream = resource.captured_req.stream

        assert resource.captured_req_body == expected_body.encode('utf-8')
        assert stream.tell() == expected_len

    def test_bounded_stream_alias(self):
        scope = testing.create_scope()
        req_event_emitter = testing.ASGIRequestEventEmitter(b'', disconnect_at=0)
        req = falcon.asgi.Request(scope, req_event_emitter)

        assert req.bounded_stream is req.stream

    def test_request_repr(self):
        scope = testing.create_scope()
        req_event_emitter = testing.ASGIRequestEventEmitter(b'', disconnect_at=0)
        req = falcon.asgi.Request(scope, req_event_emitter)

        _repr = f'<{req.__class__.__name__}: {req.method} {req.url!r}>'
        assert req.__repr__() == _repr


class BodyLengthResource:
    async def on_post(self, req, resp):
        resp.media = {'length': len(await req.stream.read())}


class MediaResource:
    async def on_post(self, req, resp):
        resp.media = await req.get_media()


async def _simulate_chunked_post(app, body, content_type=falcon.MEDIA_TEXT):
    # NOTE(ericareg): No Content-Length, so the body size is unknown.
    scope = testing.create_scope(method='POST', headers={'Content-Type': content_type})
    req_event_emitter = testing.ASGIRequestEventEmitter(body, chunk_size=4)
    resp_event_collector = testing.ASGIResponseEventCollector()

    await app(scope, req_event_emitter, resp_event_collector)

    return resp_event_collector


class TestMaxContentLength:
    @pytest.fixture
    def app(self):
        app = falcon.asgi.App()
        app.req_options.max_content_length = 10
        app.add_route('/', BodyLengthResource())
        app.add_route('/media', MediaResource())
        return app

    @pytest.mark.parametrize('body_length', [0, 1, 9, 10])
    async def test_chunked_within_limit(self, app, body_length):
        collector = await _simulate_chunked_post(app, b'x' * body_length)

        assert collector.status == 200
        assert json.loads(b''.join(collector.body_chunks)) == {'length': body_length}

    @pytest.mark.parametrize('body_length', [11, 12, SIZE_1_KB])
    async def test_chunked_exceeded(self, app, body_length):
        collector = await _simulate_chunked_post(app, b'x' * body_length)

        assert collector.status == 413
        assert json.loads(b''.join(collector.body_chunks)) == {
            'title': '413 Content Too Large',
            'description': 'The request body must not exceed 10 bytes.',
        }

    @pytest.mark.parametrize(
        'body,expected_status',
        [
            (b'{"a": 1}', 200),
            (b'{"a": "' + b'x' * 20 + b'"}', 413),
        ],
    )
    async def test_chunked_media(self, app, body, expected_status):
        collector = await _simulate_chunked_post(
            app, body, content_type=falcon.MEDIA_JSON
        )

        assert collector.status == expected_status

    async def test_exceeded_while_responder_is_reading(self):
        class ChunkedReaderResource:
            async def on_post(self, req, resp):
                # NOTE(ericareg): The responder starts processing the body,
                #   and the limit is only exceeded while reading the rest.
                self.chunks = [await req.stream.read(8)]
                try:
                    self.chunks.append(await req.stream.read())
                finally:
                    self.eof = req.stream.eof
                    self.data_after_error = await req.stream.read()

        resource = ChunkedReaderResource()
        app = falcon.asgi.App()
        app.req_options.max_content_length = 20
        app.add_route('/', resource)

        # NOTE(ericareg): No Content-Length, so the body size is unknown.
        scope = testing.create_scope(method='POST')
        req_event_emitter = testing.ASGIRequestEventEmitter(b'x' * 30, chunk_size=8)
        req_event_emitter._emit_empty_chunks = False
        resp_event_collector = testing.ASGIResponseEventCollector()

        await app(scope, req_event_emitter, resp_event_collector)

        assert resp_event_collector.status == 413
        assert b'must not exceed 20 bytes' in b''.join(resp_event_collector.body_chunks)
        assert resource.chunks == [b'x' * 8]
        assert resource.eof is True
        assert resource.data_after_error == b''
