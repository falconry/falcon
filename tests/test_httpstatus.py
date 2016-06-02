# -*- coding: utf-8

import falcon
from falcon.http_status import HTTPStatus
import falcon.testing as testing


def before_hook(req, resp, params):
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
        resp.status = falcon.HTTP_500
        resp.set_header('X-Failed', 'True')
        resp.body = 'Fail'

    def on_patch(self, req, resp):
        raise HTTPStatus(falcon.HTTP_200,
                         body=None)

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


class TestHTTPStatus(testing.TestBase):
    def before(self):
        self.resource = TestStatusResource()
        self.api.add_route('/status', self.resource)

    def test_raise_status_in_before_hook(self):
        """ Make sure we get the 200 raised by before hook """
        body = self.simulate_request('/status', method='GET', decode='utf-8')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn(('x-failed', 'False'), self.srmock.headers)
        self.assertEqual(body, 'Pass')

    def test_raise_status_in_responder(self):
        """ Make sure we get the 200 raised by responder """
        body = self.simulate_request('/status', method='POST', decode='utf-8')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn(('x-failed', 'False'), self.srmock.headers)
        self.assertEqual(body, 'Pass')

    def test_raise_status_runs_after_hooks(self):
        """ Make sure after hooks still run """
        body = self.simulate_request('/status', method='PUT', decode='utf-8')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn(('x-failed', 'False'), self.srmock.headers)
        self.assertEqual(body, 'Pass')

    def test_raise_status_survives_after_hooks(self):
        """ Make sure after hook doesn't overwrite our status """
        body = self.simulate_request('/status', method='DELETE',
                                     decode='utf-8')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn(('x-failed', 'False'), self.srmock.headers)
        self.assertEqual(body, 'Pass')

    def test_raise_status_empty_body(self):
        """ Make sure passing None to body results in empty body """
        body = self.simulate_request('/status', method='PATCH', decode='utf-8')
        self.assertEqual(body, '')


class TestHTTPStatusWithMiddleware(testing.TestBase):
    def before(self):
        self.resource = TestHookResource()

    def test_raise_status_in_process_request(self):
        """ Make sure we can raise status from middleware process request """
        class TestMiddleware:
            def process_request(self, req, resp):
                raise HTTPStatus(falcon.HTTP_200,
                                 headers={'X-Failed': 'False'},
                                 body='Pass')

        self.api = falcon.API(middleware=TestMiddleware())
        self.api.add_route('/status', self.resource)

        body = self.simulate_request('/status', method='GET', decode='utf-8')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn(('x-failed', 'False'), self.srmock.headers)
        self.assertEqual(body, 'Pass')

    def test_raise_status_in_process_resource(self):
        """ Make sure we can raise status from middleware process resource """
        class TestMiddleware:
            def process_resource(self, req, resp, resource, params):
                raise HTTPStatus(falcon.HTTP_200,
                                 headers={'X-Failed': 'False'},
                                 body='Pass')

        self.api = falcon.API(middleware=TestMiddleware())
        self.api.add_route('/status', self.resource)

        body = self.simulate_request('/status', method='GET', decode='utf-8')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn(('x-failed', 'False'), self.srmock.headers)
        self.assertEqual(body, 'Pass')

    def test_raise_status_runs_process_response(self):
        """ Make sure process_response still runs """
        class TestMiddleware:
            def process_response(self, req, resp, response):
                resp.status = falcon.HTTP_200
                resp.set_header('X-Failed', 'False')
                resp.body = 'Pass'

        self.api = falcon.API(middleware=TestMiddleware())
        self.api.add_route('/status', self.resource)

        body = self.simulate_request('/status', method='GET', decode='utf-8')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn(('x-failed', 'False'), self.srmock.headers)
        self.assertEqual(body, 'Pass')
