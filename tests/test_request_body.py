import io

import falcon
from falcon import request_helpers
import falcon.testing as testing

SIZE_1_KB = 1024


class TestRequestBody(testing.TestBase):

    def before(self):
        self.resource = testing.TestResource()
        self.api.add_route('/', self.resource)

    def test_empty_body(self):
        self.simulate_request('/', body='')
        stream = self.resource.req.stream

        stream.seek(0, 2)
        self.assertEqual(stream.tell(), 0)

    def test_tiny_body(self):
        expected_body = '.'
        self.simulate_request('', body=expected_body)
        stream = self.resource.req.stream

        actual_body = stream.read(1)
        self.assertEqual(actual_body, expected_body.encode('utf-8'))

        stream.seek(0, 2)
        self.assertEqual(stream.tell(), 1)

    def test_tiny_body_overflow(self):
        expected_body = '.'
        self.simulate_request('', body=expected_body)
        stream = self.resource.req.stream

        # Read too many bytes; shouldn't block
        actual_body = stream.read(len(expected_body) + 1)
        self.assertEqual(actual_body, expected_body.encode('utf-8'))

    def test_read_body(self):
        expected_body = testing.rand_string(SIZE_1_KB / 2, SIZE_1_KB)
        expected_len = len(expected_body)
        headers = {'Content-Length': str(expected_len)}

        self.simulate_request('', body=expected_body, headers=headers)

        content_len = self.resource.req.get_header('content-length')
        self.assertEqual(content_len, str(expected_len))

        stream = self.resource.req.stream

        actual_body = stream.read()
        self.assertEqual(actual_body, expected_body.encode('utf-8'))

        stream.seek(0, 2)
        self.assertEqual(stream.tell(), expected_len)

        self.assertEqual(stream.tell(), expected_len)

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
        self.assertEqual(len(data), 0)

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
        self.assertEqual(body.read(), expected_body)

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(body.read(2), expected_body[0:2])

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(body.read(expected_len + 1), expected_body)

        # NOTE(kgriffs): Test that reading past the end does not
        # hang, but returns the empty string.
        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        for i in range(expected_len + 1):
            expected_value = expected_body[i:i + 1] if i < expected_len else b''
            self.assertEqual(body.read(1), expected_value)

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(body.readline(), expected_lines[0])

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(body.readline(-1), expected_lines[0])

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(body.readline(expected_len + 1), expected_lines[0])

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(body.readlines(), expected_lines)

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(body.readlines(-1), expected_lines)

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(body.readlines(expected_len + 1), expected_lines)

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(next(body), expected_lines[0])

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        for i, line in enumerate(body):
            self.assertEqual(line, expected_lines[i])
