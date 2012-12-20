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

        resp['status'] = falcon.HTTP_200
        resp['body'] = self.sample_body


class TestHelloWorld(testtools.TestCase):

    def setUp(self):
        super(TestHelloWorld, self).setUp()
        self.api = falcon.Api()
        self.srmock = helpers.StartResponseMock()
        self.test_route = '/hello'

        self.on_hello = HelloRequestHandler()
        self.api.add_route(self.test_route, self.on_hello)

    def test_hello_route_negative(self):
        bogus_route = self.test_route + 'x'
        self.api(helpers.create_environ(bogus_route), self.srmock)

        # Ensure the request was NOT routed to on_hello
        self.assertFalse(self.on_hello.called)
        self.assertThat(self.srmock.status, Equals(falcon.HTTP_404))

    def test_hello_route(self):
        # Simulate a request to the attached route
        self.api(helpers.create_environ(self.test_route), self.srmock)
        resp = self.on_hello.resp

        self.assertTrue('status' in resp)
        self.assertThat(resp['status'], Equals(self.on_hello.sample_status))

        self.assertTrue('body' in resp)
        self.assertThat(resp['body'], Equals(self.on_hello.sample_body))

        # TODO: Framework adds keep-alive and either chunked or content-length

        #
        # TODO: Refactor most of the following into other classes
        #

        # TODO: Test custom error handlers - customizing error document at least
        # TODO: Test async middleware ala rproxy
        # TODO: Test setting different routes for different verbs
        # TODO: Test correct content length is set
        # TODO: Test throwing an exception from within a handler
        # TODO: Test neglecting to set a body
        # TODO: Test neglecting to set a status
        # TODO: Test setting the body to a stream, rather than a string (and content-length set to chunked?)
        # TODO: Test passing bad arguments to add_route
        # TODO: Test other kinds of routes - empty, root, multiple levels
        # TODO: Test URI-template parsing (precompile)
        # TODO: Test passing a shared dict to each mock call (e.g., db connections, config)
        #       ...and that it is passed to the request handler correctly
        # TODO: Test setting various headers, and seeing that Falcon doesn't override custom ones, but will set them if not present (or not?)
        # TODO: Test pre/post filters
        # TODO: Test error handling with standard response (for all error classes?)
        pass
