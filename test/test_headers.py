import testtools
import random

from testtools.matchers import Equals, MatchesRegex, Contains, Not

import falcon
import test.helpers as helpers

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
