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
def resource_things():
    return ThingsResource()


@pytest.fixture
def resource_misc():
    return MiscResource()


@pytest.fixture
def resource_get_with_faulty_put():
    return GetWithFaultyPutResource()


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

    def test_get(self, resource_things):
        app = falcon.APIBuilder() \
            .add_get_route('/things/{id}/stuff/{sid}', resource_things.on_get) \
            .build()
        client = testing.TestClient(app)
        response = client.simulate_request(path='/things/42/stuff/57')
        assert response.status == falcon.HTTP_204
        assert resource_things.called

    def test_put(self, resource_things):
        app = falcon.APIBuilder() \
            .add_put_route('/things/{id}/stuff/{sid}', resource_things.on_put) \
            .build()
        client = testing.TestClient(app)
        response = client.simulate_request(path='/things/42/stuff/1337', method='PUT')
        assert response.status == falcon.HTTP_201
        assert resource_things.called

    def test_post_not_allowed(self, resource_things):
        app = falcon.APIBuilder() \
            .add_get_route('/things/{id}/stuff/{sid}', resource_things.on_get) \
            .build()
        client = testing.TestClient(app)
        response = client.simulate_request(path='/things/42/stuff/1337', method='POST')
        assert response.status == falcon.HTTP_405
        assert not resource_things.called

    def test_report(self, resource_things):
        app = falcon.APIBuilder() \
            .add_method_route('REPORT', '/things/{id}/stuff/{sid}', resource_things.on_report) \
            .build()
        client = testing.TestClient(app)
        response = client.simulate_request(path='/things/42/stuff/1337', method='REPORT')
        assert response.status == falcon.HTTP_204
        assert resource_things.called

    def test_misc(self, resource_misc):
        app = falcon.APIBuilder() \
            .add_get_route('/misc', resource_misc.on_get) \
            .add_head_route('/misc', resource_misc.on_head) \
            .add_put_route('/misc', resource_misc.on_put) \
            .add_patch_route('/misc', resource_misc.on_patch) \
            .build()
        client = testing.TestClient(app)
        for method in ['GET', 'HEAD', 'PUT', 'PATCH']:
            resource_misc.called = False
            client.simulate_request(path='/misc', method=method)
            assert resource_misc.called
            assert resource_misc.req.method == method

    def test_resource_not_found(self):
        app = falcon.APIBuilder().build()
        client = testing.TestClient(app)
        for method in ['GET', 'HEAD', 'PUT', 'PATCH']:
            response = client.simulate_request(path='/stonewall', method=method)
            assert response.status == falcon.HTTP_404

    def test_methods_not_allowed_complex(self, resource_things):
        app = falcon.APIBuilder() \
            .add_get_route('/things/{id}/stuff/{sid}', resource_things.on_get) \
            .add_put_route('/things/{id}/stuff/{sid}', resource_things.on_put) \
            .build()
        client = testing.TestClient(app)
        for method in HTTP_METHODS + WEBDAV_METHODS:
            if method in ('GET', 'PUT', 'OPTIONS'):
                continue

            resource_things.called = False
            response = client.simulate_request(path='/things/84/stuff/65', method=method)

            assert not resource_things.called
            assert response.status == falcon.HTTP_405

            headers = response.headers
            assert headers['allow'] == 'GET, PUT, OPTIONS'

    def test_method_not_allowed_with_param(self, resource_get_with_faulty_put):
        app = falcon.APIBuilder() \
            .add_get_route('/get_with_param/{param}', resource_get_with_faulty_put.on_get) \
            .add_put_route('/get_with_param/{param}', resource_get_with_faulty_put.on_put) \
            .build()
        client = testing.TestClient(app)
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

    def test_default_on_options(self, resource_things):
        app = falcon.APIBuilder() \
            .add_get_route('/things/{id}/stuff/{sid}', resource_things.on_get) \
            .add_put_route('/things/{id}/stuff/{sid}', resource_things.on_put) \
            .add_head_route('/things/{id}/stuff/{sid}', resource_things.on_head) \
            .add_method_route('REPORT', '/things/{id}/stuff/{sid}', resource_things.on_report) \
            .build()
        client = testing.TestClient(app)
        response = client.simulate_request(path='/things/84/stuff/65', method='OPTIONS')
        assert response.status == falcon.HTTP_200

        headers = response.headers
        assert headers['allow'] == 'GET, HEAD, PUT, REPORT'

    def test_on_options(self, resource_misc):
        app = falcon.APIBuilder() \
            .add_options_route('/misc', resource_misc.on_options) \
            .build()
        client = testing.TestClient(app)
        response = client.simulate_request(path='/misc', method='OPTIONS')
        assert response.status == falcon.HTTP_204

        headers = response.headers
        assert headers['allow'] == 'GET'

    def test_bogus_method(self, resource_things):
        app = falcon.APIBuilder() \
            .add_get_route('/things', resource_things.on_get) \
            .add_put_route('/things', resource_things.on_put) \
            .add_head_route('/things', resource_things.on_head) \
            .add_method_route('REPORT', '/things', resource_things.on_report) \
            .build()
        client = testing.TestClient(app)
        response = client.simulate_request(path='/things', method='SETECASTRONOMY')
        assert not resource_things.called
        assert response.status == falcon.HTTP_400
