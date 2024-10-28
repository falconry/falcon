import http

import pytest

import falcon
from falcon.http_status import HTTPStatus
import falcon.testing as testing


@pytest.fixture()
def client(asgi, util):
    app = util.create_app(asgi)
    app.add_route('/status', TestStatusResource())
    return testing.TestClient(app)


@pytest.fixture()
def hook_test_client(asgi, util):
    app = util.create_app(asgi)
    app.add_route('/status', TestHookResource())
    return testing.TestClient(app)


def before_hook(req, resp, resource, params):
    raise HTTPStatus(falcon.HTTP_200, headers={'X-Failed': 'False'}, text='Pass')


def after_hook(req, resp, resource):
    resp.status = falcon.HTTP_200
    resp.set_header('X-Failed', 'False')
    resp.text = 'Pass'


def noop_after_hook(req, resp, resource):
    pass


class TestStatusResource:
    @falcon.before(before_hook)
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_500
        resp.set_header('X-Failed', 'True')
        resp.text = 'Fail'

    def on_post(self, req, resp):
        resp.status = falcon.HTTP_500
        resp.set_header('X-Failed', 'True')
        resp.text = 'Fail'

        raise HTTPStatus(falcon.HTTP_200, headers={'X-Failed': 'False'}, text='Pass')

    @falcon.after(after_hook)
    def on_put(self, req, resp):
        # NOTE(kgriffs): Test that passing a unicode status string
        # works just fine.
        resp.status = '500 Internal Server Error'
        resp.set_header('X-Failed', 'True')
        resp.text = 'Fail'

    def on_patch(self, req, resp):
        raise HTTPStatus(falcon.HTTP_200, text=None)

    @falcon.after(noop_after_hook)
    def on_delete(self, req, resp):
        raise HTTPStatus(201, headers={'X-Failed': 'False'}, text='Pass')


class TestHookResource:
    def on_get(self, req, resp):
        resp.status_code = 500
        resp.set_header('X-Failed', 'True')
        resp.text = 'Fail'

    def on_patch(self, req, resp):
        raise HTTPStatus(200, text=None)


class TestHTTPStatus:
    def test_raise_status_in_before_hook(self, client):
        """Make sure we get the 200 raised by before hook"""
        response = client.simulate_request(path='/status', method='GET')
        assert response.status == falcon.HTTP_200
        assert response.status_code == 200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_in_responder(self, client):
        """Make sure we get the 200 raised by responder"""
        response = client.simulate_request(path='/status', method='POST')
        assert response.status == falcon.HTTP_200
        assert response.status_code == 200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_runs_after_hooks(self, client):
        """Make sure after hooks still run"""
        response = client.simulate_request(path='/status', method='PUT')
        assert response.status == falcon.HTTP_200
        assert response.status_code == 200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_survives_after_hooks(self, client):
        """Make sure after hook doesn't overwrite our status"""
        response = client.simulate_request(path='/status', method='DELETE')
        assert response.status == falcon.HTTP_201
        assert response.status_code == 201
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_empty_body(self, client):
        """Make sure passing None to body results in empty body"""
        response = client.simulate_request(path='/status', method='PATCH')
        assert response.text == ''


class TestHTTPStatusWithMiddleware:
    def test_raise_status_in_process_request(self, hook_test_client):
        """Make sure we can raise status from middleware process request"""
        client = hook_test_client

        class TestMiddleware:
            def process_request(self, req, resp):
                raise HTTPStatus(
                    falcon.HTTP_200, headers={'X-Failed': 'False'}, text='Pass'
                )

            # NOTE(kgriffs): Test the side-by-side support for dual WSGI and
            #   ASGI compatibility.
            async def process_request_async(self, req, resp):
                self.process_request(req, resp)

        client.app.add_middleware(TestMiddleware())

        response = client.simulate_request(path='/status', method='GET')
        assert response.status_code == 200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_in_process_resource(self, hook_test_client):
        """Make sure we can raise status from middleware process resource"""
        client = hook_test_client

        class TestMiddleware:
            def process_resource(self, req, resp, resource, params):
                raise HTTPStatus(
                    falcon.HTTP_200, headers={'X-Failed': 'False'}, text='Pass'
                )

            async def process_resource_async(self, *args):
                self.process_resource(*args)

        # NOTE(kgriffs): Pass a list to test that add_middleware can handle it
        client.app.add_middleware([TestMiddleware()])

        response = client.simulate_request(path='/status', method='GET')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_runs_process_response(self, hook_test_client):
        """Make sure process_response still runs"""
        client = hook_test_client

        class TestMiddleware:
            def process_response(self, req, resp, resource, req_succeeded):
                resp.status = falcon.HTTP_200
                resp.set_header('X-Failed', 'False')
                resp.text = 'Pass'

            async def process_response_async(self, *args):
                self.process_response(*args)

        # NOTE(kgriffs): Pass a generic iterable to test that add_middleware
        #   can handle it.
        client.app.add_middleware(iter([TestMiddleware()]))

        response = client.simulate_request(path='/status', method='GET')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'


class NoBodyResource:
    def on_get(self, req, res):
        res.data = b'foo'
        http_status = HTTPStatus(745)
        assert http_status.status_code == 745
        raise http_status

    def on_post(self, req, res):
        res.media = {'a': 1}
        http_status = HTTPStatus(falcon.HTTP_725)
        assert http_status.status_code == 725
        raise http_status

    def on_put(self, req, res):
        res.text = 'foo'
        raise HTTPStatus(falcon.HTTP_719)


@pytest.fixture()
def body_client(asgi, util):
    app = util.create_app(asgi)
    app.add_route('/status', NoBodyResource())
    return testing.TestClient(app)


class TestNoBodyWithStatus:
    def test_data_is_set(self, body_client):
        res = body_client.simulate_get('/status')
        assert res.status == falcon.HTTP_745
        assert res.status_code == 745
        assert res.content == b''

    def test_media_is_set(self, body_client):
        res = body_client.simulate_post('/status')
        assert res.status == falcon.HTTP_725
        assert res.status_code == 725
        assert res.content == b''

    def test_body_is_set(self, body_client):
        res = body_client.simulate_put('/status')
        assert res.status == falcon.HTTP_719
        assert res.status_code == 719
        assert res.content == b''


@pytest.fixture()
def custom_status_client(asgi, util):
    def client(status):
        class Resource:
            def on_get(self, req, resp):
                resp.content_type = falcon.MEDIA_TEXT
                resp.data = b'Hello, World!'
                resp.status = status

        app = util.create_app(asgi)
        app.add_route('/status', Resource())
        return testing.TestClient(app)

    return client


@pytest.mark.parametrize(
    'status,expected_code',
    [
        (http.HTTPStatus(200), 200),
        (http.HTTPStatus(202), 202),
        (http.HTTPStatus(403), 403),
        (http.HTTPStatus(500), 500),
        (http.HTTPStatus.OK, 200),
        (http.HTTPStatus.USE_PROXY, 305),
        (http.HTTPStatus.NOT_FOUND, 404),
        (http.HTTPStatus.NOT_IMPLEMENTED, 501),
        (200, 200),
        (307, 307),
        (500, 500),
        (702, 702),
        (b'200 OK', 200),
        (b'702 Emacs', 702),
    ],
)
def test_non_string_status(custom_status_client, status, expected_code):
    client = custom_status_client(status)
    resp = client.simulate_get('/status')
    assert resp.text == 'Hello, World!'
    assert resp.status_code == expected_code


def test_deprecated_body():
    with pytest.raises(TypeError) as type_error:
        sts = HTTPStatus(falcon.HTTP_701, body='foo')

    assert 'unexpected keyword argument' in str(type_error.value)

    sts = HTTPStatus(falcon.HTTP_701, text='foo')
    assert sts.text == 'foo'
