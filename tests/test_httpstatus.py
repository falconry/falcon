# -*- coding: utf-8

import falcon
from falcon.http_status import HTTPStatus
import falcon.testing as testing


def before_hook(req, resp, resource, params):
    raise HTTPStatus(falcon.HTTP_200,
                     headers={'X-Failed': 'False'},
                     body='Pass')


def after_hook(req, resp, resource):
    resp.status = falcon.HTTP_200
    resp.set_header('X-Failed', 'False')
    resp.body = 'Pass'


def noop_after_hook(req, resp, resource):
    pass


class TestStatusResource:

    @falcon.before(before_hook)
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_500
        resp.set_header('X-Failed', 'True')
        resp.body = 'Fail'

    def on_post(self, req, resp):
        resp.status = falcon.HTTP_500
        resp.set_header('X-Failed', 'True')
        resp.body = 'Fail'

        raise HTTPStatus(falcon.HTTP_200,
                         headers={'X-Failed': 'False'},
                         body='Pass')

    @falcon.after(after_hook)
    def on_put(self, req, resp):
        # NOTE(kgriffs): Test that passing a unicode status string
        # works just fine.
        resp.status = u'500 Internal Server Error'
        resp.set_header('X-Failed', 'True')
        resp.body = 'Fail'

    def on_patch(self, req, resp):
        raise HTTPStatus(falcon.HTTP_200, body=None)

    @falcon.after(noop_after_hook)
    def on_delete(self, req, resp):
        raise HTTPStatus(falcon.HTTP_200,
                         headers={'X-Failed': 'False'},
                         body='Pass')


class TestHookResource:

    def on_get(self, req, resp):
        resp.status = falcon.HTTP_500
        resp.set_header('X-Failed', 'True')
        resp.body = 'Fail'

    def on_patch(self, req, resp):
        raise HTTPStatus(falcon.HTTP_200,
                         body=None)

    def on_delete(self, req, resp):
        raise HTTPStatus(falcon.HTTP_200,
                         headers={'X-Failed': 'False'},
                         body='Pass')


class TestHTTPStatus(object):
    def test_raise_status_in_before_hook(self):
        """ Make sure we get the 200 raised by before hook """
        app = falcon.API()
        app.add_route('/status', TestStatusResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path='/status', method='GET')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_in_responder(self):
        """ Make sure we get the 200 raised by responder """
        app = falcon.API()
        app.add_route('/status', TestStatusResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path='/status', method='POST')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_runs_after_hooks(self):
        """ Make sure after hooks still run """
        app = falcon.API()
        app.add_route('/status', TestStatusResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path='/status', method='PUT')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_survives_after_hooks(self):
        """ Make sure after hook doesn't overwrite our status """
        app = falcon.API()
        app.add_route('/status', TestStatusResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path='/status', method='DELETE')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_empty_body(self):
        """ Make sure passing None to body results in empty body """
        app = falcon.API()
        app.add_route('/status', TestStatusResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path='/status', method='PATCH')
        assert response.text == ''


class TestHTTPStatusWithMiddleware(object):
    def test_raise_status_in_process_request(self):
        """ Make sure we can raise status from middleware process request """
        class TestMiddleware:
            def process_request(self, req, resp):
                raise HTTPStatus(falcon.HTTP_200,
                                 headers={'X-Failed': 'False'},
                                 body='Pass')

        app = falcon.API(middleware=TestMiddleware())
        app.add_route('/status', TestHookResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path='/status', method='GET')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_in_process_resource(self):
        """ Make sure we can raise status from middleware process resource """
        class TestMiddleware:
            def process_resource(self, req, resp, resource, params):
                raise HTTPStatus(falcon.HTTP_200,
                                 headers={'X-Failed': 'False'},
                                 body='Pass')

        app = falcon.API(middleware=TestMiddleware())
        app.add_route('/status', TestHookResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path='/status', method='GET')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'

    def test_raise_status_runs_process_response(self):
        """ Make sure process_response still runs """
        class TestMiddleware:
            def process_response(self, req, resp, resource, req_succeeded):
                resp.status = falcon.HTTP_200
                resp.set_header('X-Failed', 'False')
                resp.body = 'Pass'

        app = falcon.API(middleware=TestMiddleware())
        app.add_route('/status', TestHookResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path='/status', method='GET')
        assert response.status == falcon.HTTP_200
        assert response.headers['x-failed'] == 'False'
        assert response.text == 'Pass'
