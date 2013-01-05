import testtools
from testtools.matchers import Equals, MatchesRegex

import falcon
import test.helpers as helpers


class HelloRequestHandler:
    sample_status = "200 OK"
    sample_body = "Hello World!"

    def __init__(self):
        self.called = False

    def __call__(self, ctx, req, resp):
        self.called = True

        self.ctx, self.req, self.resp = ctx, req, resp

        resp.status = falcon.HTTP_200
        resp.body = self.sample_body


class TestHelloWorld(helpers.TestSuite):

    def prepare(self):
        self.on_hello = HelloRequestHandler()
        self.api.add_route(self.test_route, self.on_hello)

    def test_hello_route_negative(self):
        bogus_route = self.test_route + 'x'
        self._simulate_request(bogus_route)

        # Ensure the request was NOT routed to on_hello
        self.assertFalse(self.on_hello.called)
        self.assertThat(self.srmock.status, Equals(falcon.HTTP_404))

    def test_hello_route(self):
        self._simulate_request(self.test_route)
        resp = self.on_hello.resp

        self.assertThat(resp.status, Equals(self.on_hello.sample_status))

        self.assertThat(resp.body, Equals(self.on_hello.sample_body))
