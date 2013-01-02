import testtools
import random

from testtools.matchers import Equals, MatchesRegex, Contains, Not

import falcon
import test.helpers as helpers


# TODO: Automatically set text encoding to UTF-8 for plaintext (?)
# TODO: Test setting various headers, and seeing that Falcon doesn't override custom ones, but will set them if not present (or not?)
# TODO: Test correct content length is set
# TODO: Test calling set_header with bogus arguments
# TODO: The order in which header fields with differing field names are received is not significant. However, it is "good practice" to send general-header fields first, followed by request-header or response- header fields, and ending with the entity-header fields.
# TODO: Helper functions for getting and setting common headers
# TODO: Any default headers, such as content-type?
# TODO: if status is 1xx, 204, or 404 ignore body, don't set content-length
# TODO: Test passing through all headers in req object (HTTP_* in WSGI env) - better to do lazy eval
# TODO: Header names must be lower-case on lookup - test bogus, defaults
# TODO: HTTP_HOST, if present, should be used in preference to SERVER_NAME

class RequestHandler:
    sample_status = "200 OK"
    sample_body = helpers.rand_string(0, 128 * 1024)

    def __init__(self):
        self.called = False

    def __call__(self, ctx, req, resp):
        self.called = True

        self.ctx, self.req, self.resp = ctx, req, resp

        resp.status = falcon.HTTP_200
        resp.body = self.sample_body

class TestHeaders(helpers.TestSuite):

    def prepare(self):
        self.on_hello = RequestHandler()
        self.api.add_route(self.test_route, self.on_hello)

    def test_content_length(self):
        self._simulate_request(self.test_route)

        headers = self.srmock.headers

        # Test Content-Length header set
        content_length = str(len(self.on_hello.sample_body))
        content_length_header = ('Content-Length', content_length)
        self.assertThat(headers, Contains(content_length_header))

    def test_keep_alive_http_1_1(self):
        self._simulate_request(self.test_route, protocol='HTTP/1.1')
        headers = self.srmock.headers

        # Test Keep-Alive assumed on by default (HTTP/1.1)
        connection_header = ('Connection', 'Keep-Alive')
        self.assertThat(headers, Contains(connection_header))

    def test_no_keep_alive_http_1_1(self):
        req_headers = {'Connection': 'close'}
        self._simulate_request(self.test_route, protocol='HTTP/1.1',
                               headers=req_headers)
        headers = self.srmock.headers

        # Test Keep-Alive assumed on by default (HTTP/1.1)
        connection_header = ('Connection', 'Keep-Alive')
        self.assertThat(headers, Not(Contains(connection_header)))

    def test_no_implicit_keep_alive_http_1_0(self):
        self._simulate_request(self.test_route, protocol='HTTP/1.0')
        headers = self.srmock.headers

        # Test Keep-Alive assumed on by default (HTTP/1.1)
        connection_header = ('Connection', 'Keep-Alive')
        self.assertThat(headers, Not(Contains(connection_header)))

    def test_no_explicit_keep_alive_http_1_0(self):
        req_headers = {'Connection': 'Keep-Alive'}
        self._simulate_request(self.test_route, protocol='HTTP/1.0',
                               headers=req_headers)
        headers = self.srmock.headers

        # Test Keep-Alive assumed on by default (HTTP/1.1)
        connection_header = ('Connection', 'Keep-Alive')
        self.assertThat(headers, Not(Contains(connection_header)))
