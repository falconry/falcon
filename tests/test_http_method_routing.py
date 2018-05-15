from functools import wraps

import pytest

import falcon
import falcon.testing as testing

HTTP_METHODS = (
    'CONNECT',
    'DELETE',
    'GET',
    'HEAD',
    'OPTIONS',
    'POST',
    'PUT',
    'TRACE',
    'PATCH'
)


WEBDAV_METHODS = (
    'CHECKIN',
    'CHECKOUT',
    'REPORT',
    'UNCHECKIN',
    'UPDATE',
    'VERSION-CONTROL',
)


@pytest.fixture
def stonewall():
    return Stonewall()


@pytest.fixture
def resource_things():
    return ThingsResource()


@pytest.fixture
def resource_misc():
    return MiscResource()


@pytest.fixture
def resource_get_with_faulty_put():
    return GetWithFaultyPutResource()


@pytest.fixture
def client():
    app = falcon.API()

    app.add_route('/stonewall', Stonewall())

    resource_things = ThingsResource()
    app.add_route('/things', resource_things)
    app.add_route('/things/{id}/stuff/{sid}', resource_things)

    resource_misc = MiscResource()
    app.add_route('/misc', resource_misc)

    resource_get_with_faulty_put = GetWithFaultyPutResource()
    app.add_route('/get_with_param/{param}', resource_get_with_faulty_put)
    return testing.TestClient(app)


class ThingsResource(object):
    def __init__(self):
        self.called = False

        # Test non-callable attribute
        self.on_patch = {}

    # Field names ordered differently than in uri template
    def on_get(self, req, resp, sid, id):
        self.called = True

        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_204

    # Field names ordered the same as in uri template
    def on_head(self, req, resp, id, sid):
        self.called = True

        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_204

    def on_put(self, req, resp, id, sid):
        self.called = True

        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_201

    def on_report(self, req, resp, id, sid):
        self.called = True

        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_204


class Stonewall(object):
    pass


def capture(func):
    @wraps(func)
    def with_capture(*args, **kwargs):
        self = args[0]
        self.called = True
        self.req, self.resp = args[1:]
        func(*args, **kwargs)

    return with_capture


def selfless_decorator(func):
    def faulty(req, resp, foo, bar):
        pass

    return faulty


class MiscResource(object):
    def __init__(self):
        self.called = False

    @capture
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_204

    @capture
    def on_head(self, req, resp):
        resp.status = falcon.HTTP_204

    @capture
    def on_put(self, req, resp):
        resp.status = falcon.HTTP_400

    @capture
    def on_patch(self, req, resp):
        pass

    def on_options(self, req, resp):
        # NOTE(kgriffs): The default responder returns 200
        resp.status = falcon.HTTP_204

        # NOTE(kgriffs): This is incorrect, but only return GET so
        # that we can verify that the default OPTIONS responder has
        # been overridden.
        resp.set_header('allow', 'GET')


class GetWithFaultyPutResource(object):
    def __init__(self):
        self.called = False

    @capture
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_204

    def on_put(self, req, resp, param):
        raise TypeError()


class FaultyDecoratedResource(object):

    @selfless_decorator
    def on_get(self, req, resp):
        pass


class TestHttpMethodRouting(object):

    def test_get(self, client, resource_things):
        client.app.add_route('/things', resource_things)
        client.app.add_route('/things/{id}/stuff/{sid}', resource_things)
        response = client.simulate_request(path='/things/42/stuff/57')
        assert response.status == falcon.HTTP_204
        assert resource_things.called

    def test_put(self, client, resource_things):
        client.app.add_route('/things', resource_things)
        client.app.add_route('/things/{id}/stuff/{sid}', resource_things)
        response = client.simulate_request(path='/things/42/stuff/1337', method='PUT')
        assert response.status == falcon.HTTP_201
        assert resource_things.called

    def test_post_not_allowed(self, client, resource_things):
        client.app.add_route('/things', resource_things)
        client.app.add_route('/things/{id}/stuff/{sid}', resource_things)
        response = client.simulate_request(path='/things/42/stuff/1337', method='POST')
        assert response.status == falcon.HTTP_405
        assert not resource_things.called

    def test_report(self, client, resource_things):
        client.app.add_route('/things', resource_things)
        client.app.add_route('/things/{id}/stuff/{sid}', resource_things)
        response = client.simulate_request(path='/things/42/stuff/1337', method='REPORT')
        assert response.status == falcon.HTTP_204
        assert resource_things.called

    def test_misc(self, client, resource_misc):
        client.app.add_route('/misc', resource_misc)
        for method in ['GET', 'HEAD', 'PUT', 'PATCH']:
            resource_misc.called = False
            client.simulate_request(path='/misc', method=method)
            assert resource_misc.called
            assert resource_misc.req.method == method

    def test_methods_not_allowed_simple(self, client, stonewall):
        client.app.add_route('/stonewall', stonewall)
        for method in ['GET', 'HEAD', 'PUT', 'PATCH']:
            response = client.simulate_request(path='/stonewall', method=method)
            assert response.status == falcon.HTTP_405

    def test_methods_not_allowed_complex(self, client, resource_things):
        client.app.add_route('/things', resource_things)
        client.app.add_route('/things/{id}/stuff/{sid}', resource_things)
        for method in HTTP_METHODS + WEBDAV_METHODS:
            if method in ('GET', 'PUT', 'HEAD', 'OPTIONS', 'REPORT'):
                continue

            resource_things.called = False
            response = client.simulate_request(path='/things/84/stuff/65', method=method)

            assert not resource_things.called
            assert response.status == falcon.HTTP_405

            headers = response.headers
            assert headers['allow'] == 'GET, HEAD, PUT, REPORT, OPTIONS'

    def test_method_not_allowed_with_param(self, client, resource_get_with_faulty_put):
        client.app.add_route('/get_with_param/{param}', resource_get_with_faulty_put)
        for method in HTTP_METHODS + WEBDAV_METHODS:
            if method in ('GET', 'PUT', 'OPTIONS'):
                continue

            resource_get_with_faulty_put.called = False
            response = client.simulate_request(
                method=method,
                path='/get_with_param/bogus_param',
            )

            assert not resource_get_with_faulty_put.called
            assert response.status == falcon.HTTP_405

            headers = response.headers
            assert headers['allow'] == 'GET, PUT, OPTIONS'

    def test_default_on_options(self, client, resource_things):
        client.app.add_route('/things', resource_things)
        client.app.add_route('/things/{id}/stuff/{sid}', resource_things)
        response = client.simulate_request(path='/things/84/stuff/65', method='OPTIONS')
        assert response.status == falcon.HTTP_200

        headers = response.headers
        assert headers['allow'] == 'GET, HEAD, PUT, REPORT'

    def test_on_options(self, client):
        response = client.simulate_request(path='/misc', method='OPTIONS')
        assert response.status == falcon.HTTP_204

        headers = response.headers
        assert headers['allow'] == 'GET'

    def test_bogus_method(self, client, resource_things):
        client.app.add_route('/things', resource_things)
        client.app.add_route('/things/{id}/stuff/{sid}', resource_things)
        response = client.simulate_request(path='/things', method='SETECASTRONOMY')
        assert not resource_things.called
        assert response.status == falcon.HTTP_400
