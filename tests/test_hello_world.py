import testtools
from testtools.matchers import Equals, MatchesRegex

import falcon
import helpers

def _is_iterable(thing):
    try:
        for i in thing:
            break

        return True
    except:
        return False

class StartResponseMock:
    def __init__(self):
        self._called = 0
        self.last_status = None
        self.last_headers = None

    def __call__(self, status, headers):
        self._called += 1
        self.last_status = status
        self.last_headers = headers

    def call_count(self):
        return self._called

class RequestHandlerMock:
    sample_status = "200 OK"
    sample_body = "Hello World!"

    def __init__(self):
        self.context = None

    def __call__(self, ctx):
        self.context = ctx
        ctx.resp_status = falcon.HTTP_200
        ctx.resp_body = self.sample_body

# TODO: Need a test for pre/post filters

class TestHelloWorld(testtools.TestCase):

    def test_wsgi(self):
        api = falcon.Api()
        mock = StartResponseMock()

        # Simulate a web request (normally done though a WSGI server)
        response = api(helpers.create_environ(), mock)

        # Verify the response is iterable per PEP 333
        self.assertTrue(_is_iterable(response))

        # Make sure start_response was passed a valid status string
        self.assertIs(mock.call_count(), 1)
        self.assertTrue(isinstance(mock.last_status, basestring))
        self.assertThat(mock.last_status, MatchesRegex('^\d+[a-zA-Z\s]+$'))

        # Verify headers is a list of tuples, each containing a pair of strings
        self.assertTrue(isinstance(mock.last_headers, list))
        if len(mock.last_headers) != 0:
            header = mock.last_headers[0]
            self.assertTrue(isinstance(header, tuple))
            self.assertThat(len(header), Equals(2))
            self.assertTrue(isinstance(header[0], basestring))
            self.assertTrue(isinstance(header[1], basestring))

    def test_add_route(self):
        # todo: add a single "hello world" route, make sure it responds well,
        # and that the framework automatically adds appropriate headers
        api = falcon.Api()
        mock = StartResponseMock()

        test_route = '/hello'
        on_hello = RequestHandlerMock()
        api.add_route(test_route, on_hello)

        # Simulate a web request (normally done though a WSGI server)
        api(helpers.create_environ(test_route + 'x'), mock)

        # Ensure the request was NOT routed to on_hello
        self.assertFalse(on_hello.context)

        # TODO: Check for 404 not found response status with bad path shown (?)
        # TODO: Refactor this test - maybe put into other classes

        # Simulate a request to the attached route
        api(helpers.create_environ(test_route), mock)
        ctx = on_hello.context

        self.assertThat(ctx.resp_status, Equals(on_hello.sample_status))
        self.assertThat(ctx.resp_body, Equals(on_hello.sample_body))

        # TODO: Test correct content length is set
        # TODO: Test throwing an exception from within a handler
        # TODO: Test neglecting to set a body
        # TODO: Test neglecting to set a status
        # TODO: Test setting the body to a stream, rather than a string (and content-length set to chunked?)
        # TODO: Test passing bad arguments to add_route
        # TODO: Test other kinds of routes - empty, root, multiple levels
        # TODO: Test URI-template parsing (precompile)
        # TODO: Test passing a shared dict to each mock call (e.g., db connections, config)
        # TODO: Test setting various headers, and seeing that Falcon doesn't override custom ones, but will set them if not present (or not?)
        pass
