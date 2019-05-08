import pytest

import falcon
from falcon import testing
import falcon.constants
from falcon.routing.util import map_http_methods

FALCON_CUSTOM_HTTP_METHODS = ['FOO', 'BAR']


@pytest.fixture
def resource_things():
    return ThingsResource()


@pytest.fixture
def client():
    app = falcon.API()
    app.add_route('/things', ThingsResource())
    return testing.TestClient(app)


class ThingsResource:
    def __init__(self):
        self.called = False

        # Test non-callable attribute
        self.on_patch = {}

    # Field names ordered differently than in uri template
    def on_foo(self, req, resp):
        self.called = True
        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_204


def setup_module(module):
    falcon.constants.COMBINED_METHODS += FALCON_CUSTOM_HTTP_METHODS


def teardown_module(module):
    for method in FALCON_CUSTOM_HTTP_METHODS:
        index = falcon.constants.COMBINED_METHODS.index(method)
        falcon.constants.COMBINED_METHODS.pop(index)


def test_map_http_methods(resource_things, monkeypatch):
    method_map = map_http_methods(resource_things)
    assert 'FOO' in method_map
    assert 'BAR' not in method_map


class TestHttpMethodRouting:

    def test_foo(self, client, resource_things):
        """FOO is a supported method, so returns HTTP_204"""
        client.app.add_route('/things', resource_things)
        response = client.simulate_request(path='/things', method='FOO')
        assert 'FOO' in falcon.constants.COMBINED_METHODS
        assert response.status == falcon.HTTP_204
        assert resource_things.called

    def test_bar(self, client, resource_things):
        """BAR is not supported by ResourceThing"""
        client.app.add_route('/things', resource_things)
        response = client.simulate_request(path='/things', method='BAR')
        assert 'BAR' in falcon.constants.COMBINED_METHODS
        assert response.status == falcon.HTTP_405
