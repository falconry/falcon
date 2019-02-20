import pytest

import falcon
from falcon import testing


def test_custom_router_add_route_should_be_used():
    check = []

    class CustomRouter(object):
        def add_route(self, uri_template, *args, **kwargs):
            check.append(uri_template)

        def find(self, uri):
            pass

    app = falcon.API(router=CustomRouter())
    app.add_route('/test', 'resource')

    assert len(check) == 1
    assert '/test' in check


def test_custom_router_find_should_be_used():

    def resource(req, resp, **kwargs):
        resp.body = '{{"uri_template": "{0}"}}'.format(req.uri_template)

    class CustomRouter(object):
        def __init__(self):
            self.reached_backwards_compat = False

        def find(self, uri, req=None):
            if uri == '/test/42':
                return resource, {'GET': resource}, {}, '/test/{id}'

            if uri == '/test/42/no-uri-template':
                return resource, {'GET': resource}, {}, None

            if uri == '/test/42/uri-template/backwards-compat':
                return resource, {'GET': resource}, {}

            if uri == '/404/backwards-compat':
                self.reached_backwards_compat = True
                return (None, None, None)

            return None

    router = CustomRouter()
    app = falcon.API(router=router)
    client = testing.TestClient(app)

    response = client.simulate_request(path='/test/42')
    assert response.content == b'{"uri_template": "/test/{id}"}'

    response = client.simulate_request(path='/test/42/no-uri-template')
    assert response.content == b'{"uri_template": "None"}'

    response = client.simulate_request(path='/test/42/uri-template/backwards-compat')
    assert response.content == b'{"uri_template": "None"}'

    for uri in ('/404', '/404/backwards-compat'):
        response = client.simulate_request(path=uri)
        assert not response.content
        assert response.status == falcon.HTTP_404

    assert router.reached_backwards_compat


def test_can_pass_additional_params_to_add_route():

    check = []

    class CustomRouter(object):
        def add_route(self, uri_template, resource, **kwargs):
            name = kwargs['name']
            self._index = {name: uri_template}
            check.append(name)

        def find(self, uri):
            pass

    app = falcon.API(router=CustomRouter())
    app.add_route('/test', 'resource', name='my-url-name')

    assert len(check) == 1
    assert 'my-url-name' in check

    # NOTE(kgriffs): Extra values must be passed as kwargs, since that makes
    #   it a lot easier for overriden methods to simply ignore options they
    #   don't care about.
    with pytest.raises(TypeError):
        app.add_route('/test', 'resource', 'xarg1', 'xarg2')


def test_custom_router_takes_req_positional_argument():
    def responder(req, resp):
        resp.body = 'OK'

    class CustomRouter(object):
        def find(self, uri, req):
            if uri == '/test' and isinstance(req, falcon.Request):
                return responder, {'GET': responder}, {}, None

    router = CustomRouter()
    app = falcon.API(router=router)
    client = testing.TestClient(app)
    response = client.simulate_request(path='/test')
    assert response.content == b'OK'


def test_custom_router_takes_req_keyword_argument():
    def responder(req, resp):
        resp.body = 'OK'

    class CustomRouter(object):
        def find(self, uri, req=None):
            if uri == '/test' and isinstance(req, falcon.Request):
                return responder, {'GET': responder}, {}, None

    router = CustomRouter()
    app = falcon.API(router=router)
    client = testing.TestClient(app)
    response = client.simulate_request(path='/test')
    assert response.content == b'OK'
