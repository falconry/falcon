import json

import falcon
from falcon import testing


class TypeResource(testing.SimpleTestResource):
    """A simple resource to return the posted request body."""
    @falcon.before(testing.capture_responder_args)
    def on_post(self, req, resp, **kwargs):
        resp.status = falcon.HTTP_200
        # NOTE(masterkale): No size needs to be specified here because we're
        # emulating a stream read in production.
        resp.body = json.dumps({'data': req.bounded_stream.read().decode('utf-8')})


class TestWsgiRefInputWrapper(object):
    def test_resources_can_read_request_stream_during_tests(self):
        """Make sure we can perform a simple request during testing.

        Originally, testing would fail after performing a request because no
        size was specified when calling `wsgiref.validate.InputWrapper.read()`
        via `req.stream.read()`"""
        app = falcon.API()
        type_route = '/type'
        app.add_route(type_route, TypeResource())
        client = testing.TestClient(app)

        result = client.simulate_post(path=type_route, body='hello')

        assert result.status == falcon.HTTP_200
        assert result.json == {'data': 'hello'}
