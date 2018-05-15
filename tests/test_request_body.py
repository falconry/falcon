import io
from wsgiref.validate import InputWrapper

import pytest

import falcon
from falcon import request_helpers
import falcon.request
import falcon.testing as testing

SIZE_1_KB = 1024


@pytest.fixture
def resource():
    return testing.SimpleTestResource()


@pytest.fixture
def client():
    app = falcon.API()
    return testing.TestClient(app)


class TestRequestBody(object):
    def _get_wrapped_stream(self, req):
        # Getting wrapped wsgi.input:
        stream = req.stream
        if isinstance(stream, request_helpers.BoundedStream):
            stream = stream.stream
        if isinstance(stream, InputWrapper):
            stream = stream.input
        if isinstance(stream, io.BytesIO):
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
        expected_body = testing.rand_string(SIZE_1_KB / 2, SIZE_1_KB)
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
        data = testing.rand_string(SIZE_1_KB / 2, SIZE_1_KB)
        expected_body = data.encode('utf-8')
        expected_len = len(expected_body)

        # NOTE(kgriffs): Append newline char to each line
        # to match readlines behavior
        expected_lines = [(line + '\n').encode('utf-8')
                          for line in data.split('\n')]

        # NOTE(kgriffs): Remove trailing newline to simulate
        # what readlines does
        expected_lines[-1] = expected_lines[-1][:-1]

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        assert body.read() == expected_body

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        assert body.read(2) == expected_body[0:2]

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        assert body.read(expected_len + 1) == expected_body

        # NOTE(kgriffs): Test that reading past the end does not
        # hang, but returns the empty string.
        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        for i in range(expected_len + 1):
            expected_value = expected_body[i:i + 1] if i < expected_len else b''
            assert body.read(1) == expected_value

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        assert body.readline() == expected_lines[0]

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        assert body.readline(-1) == expected_lines[0]

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        assert body.readline(expected_len + 1) == expected_lines[0]

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        assert body.readlines() == expected_lines

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        assert body.readlines(-1) == expected_lines

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        assert body.readlines(expected_len + 1) == expected_lines

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        assert next(body) == expected_lines[0]

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        for i, line in enumerate(body):
            assert line == expected_lines[i]

    def test_request_repr(self):
        environ = testing.create_environ()
        req = falcon.Request(environ)
        _repr = '<%s: %s %r>' % (req.__class__.__name__, req.method, req.url)
        assert req.__repr__() == _repr
