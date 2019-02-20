try:
    import ujson as json
except ImportError:
    import json

import pytest

import falcon
from falcon import testing


@pytest.fixture
def client():
    app = falcon.API()
    app.add_route('/type', TypeResource())
    return testing.TestClient(app)


@pytest.fixture
def builder_client():
    resource = TypeResource()
    app = falcon.APIBuilder() \
        .add_post_route('/type', resource.on_post) \
        .build()
    testing.TestClient(app)


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


class TestWsgiRefInputWrapper(object):
    @pytest.mark.parametrize('client', [
        'client',
        'builder_client'
    ], indirect=True)
    def test_resources_can_read_request_stream_during_tests(self, client):
        """Make sure we can perform a simple request during testing.

        Originally, testing would fail after performing a request because no
        size was specified when calling `wsgiref.validate.InputWrapper.read()`
        via `req.stream.read()`"""

        result = client.simulate_post(path='/type', body='hello')

        assert result.status == falcon.HTTP_200
        assert result.json == {'data': 'hello'}
