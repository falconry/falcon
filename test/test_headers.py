import testtools
from testtools.matchers import Equals, MatchesRegex

import falcon
import test.helpers as helpers

# TODO: Framework adds keep-alive and either chunked or content-length
# TODO: Test setting various headers, and seeing that Falcon doesn't override custom ones, but will set them if not present (or not?)
# TODO: Test correct content length is set

class RequestHandler:
    sample_status = "200 OK"
    sample_body = "Hello World!"

    def __init__(self):
        self.called = False

    def __call__(self, ctx, req, resp):
        self.called = True

        self.ctx, self.req, self.resp = ctx, req, resp

        resp['status'] = falcon.HTTP_200
        resp['body'] = self.sample_body

class TestHeaders(testtools.TestCase):

    # TODO: Figure out a way to DRY this statement - maybe via subclassing
    def setUp(self):
        super(TestHeaders, self).setUp()
        self.api = falcon.Api()
        self.srmock = helpers.StartResponseMock()
        self.test_route = '/' + self.getUniqueString()

        self.on_hello = RequestHandler()
        self.api.add_route(self.test_route, self.on_hello)


    def test_auto_headers(self):
        # TODO: Figure out a way to DRY this statement
        self.api(helpers.create_environ(self.test_route), self.srmock)

        pass