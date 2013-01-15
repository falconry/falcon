import io

from testtools.matchers import Contains

import falcon
from . import helpers


class HelloResource:
    sample_status = '200 OK'
    sample_body = 'Hello World! ' + helpers.rand_string(0, 256 * 1024)

    def __init__(self, mode):
        self.called = False
        self.mode = mode

    def on_get(self, req, resp):
        self.called = True

        self.req, self.resp = req, resp

        resp.status = falcon.HTTP_200

        if 'stream' in self.mode:
            raw_body = self.sample_body.encode('utf-8')
            resp.stream = io.BytesIO(raw_body)

            if 'stream_len' in self.mode:
                resp.stream_len = len(raw_body)

        if 'body' in self.mode:
            resp.body = self.sample_body


class NoStatusResource:
    def on_get(self, req, resp):
        resp.body = 'Oops'
        pass


class TestHelloWorld(helpers.TestSuite):

    def prepare(self):
        self.resource = HelloResource('body')
        self.api.add_route(self.test_route, self.resource)

        self.chunked_resource = HelloResource('stream')
        self.api.add_route('/chunked-stream', self.chunked_resource)

        self.stream_resource = HelloResource('stream, stream_len')
        self.api.add_route('/stream', self.stream_resource)

        self.no_status_resource = NoStatusResource()
        self.api.add_route('/nostatus', self.no_status_resource)

        self.root_resource = helpers.TestResource()
        self.api.add_route('', self.root_resource)

    def test_empty_route(self):
        self._simulate_request('')
        self.assertTrue(self.root_resource.called)

    def test_route_negative(self):
        bogus_route = self.test_route + 'x'
        self._simulate_request(bogus_route)

        # Ensure the request was NOT routed to resource
        self.assertFalse(self.resource.called)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_body(self):
        self._simulate_request(self.test_route)
        resp = self.resource.resp

        self.assertEquals(self.srmock.status, self.resource.sample_status)
        self.assertEquals(resp.status, self.resource.sample_status)
        self.assertEquals(resp.body, self.resource.sample_body)

    def test_stream_chunked(self):
        src = self._simulate_request('/chunked-stream')

        dest = io.BytesIO()
        for chunk in src:
            dest.write(chunk)

        self.assertEqual(dest.getvalue().encode('utf-8'),
                         self.chunked_resource.sample_body.encode('utf-8'))

        for header in self.srmock.headers:
            self.assertNotEqual(header[0].lower(), 'content-length')

    def test_stream_known_len(self):
        src = self._simulate_request('/stream')

        dest = io.BytesIO()
        for chunk in src:
            dest.write(chunk)

        expected_len = self.stream_resource.resp.stream_len
        content_length = ('Content-Length', str(expected_len))
        self.assertThat(self.srmock.headers, Contains(content_length))
        self.assertEqual(dest.tell(), expected_len)

        self.assertEqual(dest.getvalue().encode('utf-8'),
                         self.chunked_resource.sample_body.encode('utf-8'))

    def test_status_not_set(self):
        body = self._simulate_request('/nostatus')

        self.assertEqual(body, [])
        self.assertEqual(self.srmock.status, falcon.HTTP_500)
