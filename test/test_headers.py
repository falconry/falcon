import testtools
import random

from testtools.matchers import Equals, MatchesRegex, Contains

import falcon
import test.helpers as helpers

# TODO: Framework adds keep-alive and either chunked or content-length
# TODO: Test setting various headers, and seeing that Falcon doesn't override custom ones, but will set them if not present (or not?)
# TODO: Test correct content length is set
# TODO: Test calling set_header with bogus arguments
# TODO: The order in which header fields with differing field names are received is not significant. However, it is "good practice" to send general-header fields first, followed by request-header or response- header fields, and ending with the entity-header fields.
# TODO: Helper functions for getting and setting common headers
# TODO: Any default headers, such as content-type?
# TODO: if status is 1xx, 204, or 404 ignore body, don't set content-length

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

    def test_auto_headers(self):
        self._simulate_request(self.test_route)

        headers = self.srmock.headers

        content_length = ('Content-Length', str(len(self.on_hello.sample_body)))
        self.assertThat(headers, Contains(content_length))


