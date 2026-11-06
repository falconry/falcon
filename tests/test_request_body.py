import io
import json
from wsgiref.validate import InputWrapper

import pytest

import falcon
import falcon.request
from falcon.stream import BoundedStream
import falcon.testing as testing

SIZE_1_KB = 1024


@pytest.fixture
def resource():
    return testing.SimpleTestResource()


@pytest.fixture
def client():
    app = falcon.App()
    return testing.TestClient(app)


class TestRequestBody:
    def _get_wrapped_stream(self, req):
        # Getting wrapped wsgi.input:
        stream = req.stream
        if isinstance(stream, BoundedStream):
            stream = stream.stream
        if isinstance(stream, InputWrapper):
            stream = stream.input

        return stream

    def test_empty_body(self, client, resource):
        client.app.add_route('/', resource)
        client.simulate_request(path='/', body='')
        stream = self._get_wrapped_stream(resource.captured_req)
        assert stream.tell() == 0

    def test_tiny_body(self, client, resource):
        client.app.add_route('/', resource)
        expected_body = '.'
        client.simulate_request(path='/', body=expected_body)
        stream = self._get_wrapped_stream(resource.captured_req)

        actual_body = stream.read(1)
        assert actual_body == expected_body.encode('utf-8')

        assert stream.tell() == 1

    def test_tiny_body_overflow(self, client, resource):
        client.app.add_route('/', resource)
        expected_body = '.'
        client.simulate_request(path='/', body=expected_body)
        stream = self._get_wrapped_stream(resource.captured_req)

        # Read too many bytes; shouldn't block
        actual_body = stream.read(len(expected_body) + 1)
        assert actual_body == expected_body.encode('utf-8')

    def test_read_body(self, client, resource):
        client.app.add_route('/', resource)
        expected_body = testing.rand_string(SIZE_1_KB // 2, SIZE_1_KB)
        expected_len = len(expected_body)
        headers = {'Content-Length': str(expected_len)}

        client.simulate_request(path='/', body=expected_body, headers=headers)

        content_len = resource.captured_req.get_header('content-length')
        assert content_len == str(expected_len)

        stream = self._get_wrapped_stream(resource.captured_req)

        actual_body = stream.read()
        assert actual_body == expected_body.encode('utf-8')

        stream.seek(0, 2)
        assert stream.tell() == expected_len

        assert stream.tell() == expected_len

    def test_bounded_stream_property_empty_body(self):
        """Test that we can get a bounded stream outside of wsgiref."""
        environ = testing.create_environ()
        req = falcon.Request(environ)

        bounded_stream = req.bounded_stream

        # NOTE(kgriffs): Verify that we aren't creating a new object
        # each time the property is called. Also ensures branch
        # coverage of the property implementation.
        assert bounded_stream is req.bounded_stream
        data = bounded_stream.read()
        assert len(data) == 0

    def test_body_stream_wrapper(self):
        data = testing.rand_string(SIZE_1_KB // 2, SIZE_1_KB)
        expected_body = data.encode('utf-8')
        expected_len = len(expected_body)

        # NOTE(kgriffs): Append newline char to each line
        # to match readlines behavior
        expected_lines = [(line + '\n').encode('utf-8') for line in data.split('\n')]

        # NOTE(kgriffs): Remove trailing newline to simulate
        # what readlines does
        expected_lines[-1] = expected_lines[-1][:-1]

        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        assert body.read() == expected_body

        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        assert body.read(2) == expected_body[0:2]

        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        assert body.read(expected_len + 1) == expected_body

        # NOTE(kgriffs): Test that reading past the end does not
        # hang, but returns the empty string.
        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        for i in range(expected_len + 1):
            expected_value = expected_body[i : i + 1] if i < expected_len else b''
            assert body.read(1) == expected_value

        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        assert body.readline() == expected_lines[0]

        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        assert body.readline(-1) == expected_lines[0]

        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        assert body.readline(expected_len + 1) == expected_lines[0]

        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        assert body.readlines() == expected_lines

        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        assert body.readlines(-1) == expected_lines

        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        assert body.readlines(expected_len + 1) == expected_lines

        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        assert next(body) == expected_lines[0]

        stream = io.BytesIO(expected_body)
        body = BoundedStream(stream, expected_len)
        for i, line in enumerate(body):
            assert line == expected_lines[i]

    def test_request_repr(self):
        environ = testing.create_environ()
        req = falcon.Request(environ)
        _repr = f'<{req.__class__.__name__}: {req.method} {req.url!r}>'
        assert req.__repr__() == _repr


class BodyLengthResource:
    def on_post(self, req, resp):
        resp.media = {'length': len(req.bounded_stream.read())}


class BodyLengthResourceAsync:
    async def on_post(self, req, resp):
        resp.media = {'length': len(await req.stream.read())}


class TestMaxContentLength:
    @pytest.fixture
    def app(self, asgi, util):
        app = util.create_app(asgi)
        resource = BodyLengthResourceAsync() if asgi else BodyLengthResource()
        app.add_route('/', resource)
        return app

    def test_disabled_by_default(self, app):
        assert app.req_options.max_content_length is None

        resp = testing.simulate_post(app, '/', body=b'x' * SIZE_1_KB)
        assert resp.status_code == 200
        assert resp.json == {'length': SIZE_1_KB}

    @pytest.mark.parametrize(
        'max_content_length,body_length',
        [(0, 0), (10, 0), (10, 1), (10, 9), (10, 10)],
    )
    def test_within_limit(self, app, max_content_length, body_length):
        app.req_options.max_content_length = max_content_length

        resp = testing.simulate_post(app, '/', body=b'x' * body_length)
        assert resp.status_code == 200
        assert resp.json == {'length': body_length}

    @pytest.mark.parametrize(
        'max_content_length,body_length',
        [(0, 1), (10, 11), (10, SIZE_1_KB)],
    )
    def test_exceeded(self, app, max_content_length, body_length):
        app.req_options.max_content_length = max_content_length

        resp = testing.simulate_post(app, '/', body=b'x' * body_length)
        assert resp.status_code == 413
        assert resp.json == {
            'title': '413 Content Too Large',
            'description': (
                f'The request body must not exceed {max_content_length} bytes.'
            ),
        }

    def test_wsgi_without_content_length(self, util):
        app = util.create_app(False)
        app.req_options.max_content_length = 10
        app.add_route('/', BodyLengthResource())

        env = testing.create_environ(method='POST', body=b'x' * 30)
        del env['CONTENT_LENGTH']
        start_response = testing.StartResponseMock()
        body = b''.join(app(env, start_response))

        # NOTE(ericareg): WSGI apps treat a body without Content-Length as
        #   empty, so there is nothing to enforce.
        assert start_response.status == falcon.HTTP_200
        assert json.loads(body) == {'length': 0}
