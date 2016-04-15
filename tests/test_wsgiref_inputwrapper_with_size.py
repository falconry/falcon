import json

import falcon
from falcon import testing


class TypeResource(testing.SimpleTestResource):
    """A simple resource to return the posted request body."""
    @falcon.before(testing.capture_responder_args)
    def on_post(self, req, resp, **kwargs):
        resp.status = falcon.HTTP_200
        # NOTE(masterkale): No size needs to be specified here because we're
        # emulating a stream read in production. The request should be wrapped
        # well enough to automatically specify a size when calling `read()`
        # during either production or when running tests
        resp.body = json.dumps({'data': req.stream.read().decode('utf-8')})


class TestWsgiRefInputWrapper(testing.TestCase):
    def setUp(self):
        super(TestWsgiRefInputWrapper, self).setUp()

        # Set up a route to our TypeResoure
        self.type_route = '/type'
        self.api.add_route(self.type_route, TypeResource())

    def test_resources_can_read_request_stream_during_tests(self):
        """Make sure we can perform a simple request during testing.

        Originally, testing would fail after performing a request because no
        size was specified when calling `wsgiref.validate.InputWrapper.read()`
        via `req.stream.read()`"""
        result = self.simulate_post(path=self.type_route, body='hello')

        self.assertEqual(result.status, falcon.HTTP_200)
        self.assertEqual(result.json, {'data': 'hello'})
