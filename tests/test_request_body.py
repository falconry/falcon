import io
import multiprocessing
from wsgiref import simple_server

import requests

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

    def test_read_socket_body(self):
        expected_body = testing.rand_string(SIZE_1_KB / 2, SIZE_1_KB)

        def server():
            class Echo(object):
                def on_post(self, req, resp):
                    # wsgiref socket._fileobject blocks when len not given,
                    # but Falcon is smarter than that. :D
                    body = req.stream.read()
                    resp.body = body

                def on_put(self, req, resp):
                    # wsgiref socket._fileobject blocks when len too long,
                    # but Falcon should work around that for me.
                    body = req.stream.read(req.content_length + 1)
                    resp.body = body

            api = falcon.API()
            api.add_route('/echo', Echo())

            httpd = simple_server.make_server('127.0.0.1', 8989, api)
            httpd.serve_forever()

        process = multiprocessing.Process(target=server)
        process.daemon = True
        process.start()

        # Let it boot
        process.join(1)

        url = 'http://127.0.0.1:8989/echo'
        resp = requests.post(url, data=expected_body)
        self.assertEqual(resp.text, expected_body)

        resp = requests.put(url, data=expected_body)
        self.assertEqual(resp.text, expected_body)

        process.terminate()

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

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(body.readline(), expected_lines[0])

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(body.readlines(), expected_lines)

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        self.assertEqual(next(body), expected_lines[0])

        stream = io.BytesIO(expected_body)
        body = request_helpers.Body(stream, expected_len)
        for i, line in enumerate(body):
            self.assertEqual(line, expected_lines[i])
