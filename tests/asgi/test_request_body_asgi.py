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

    def test_read_body(self, client, resource):
        client.app.add_route('/', resource)
        expected_body = testing.rand_string(SIZE_1_KB / 2, SIZE_1_KB)
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
        req_event_emitter = testing.ASGIRequestEventEmitter(b'', 0)
        req = falcon.asgi.Request(scope, req_event_emitter)

        assert req.bounded_stream is req.stream

    def test_request_repr(self):
        scope = testing.create_scope()
        req_event_emitter = testing.ASGIRequestEventEmitter(b'', 0)
        req = falcon.asgi.Request(scope, req_event_emitter)

        _repr = '<%s: %s %r>' % (req.__class__.__name__, req.method, req.url)
        assert req.__repr__() == _repr
