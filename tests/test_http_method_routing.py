from functools import wraps

from testtools.matchers import Contains

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


class TestHttpMethodRouting(testing.TestBase):

    def before(self):
        self.api.add_route('/stonewall', Stonewall())

        self.resource_things = ThingsResource()
        self.api.add_route('/things', self.resource_things)
        self.api.add_route('/things/{id}/stuff/{sid}', self.resource_things)

        self.resource_misc = MiscResource()
        self.api.add_route('/misc', self.resource_misc)

        self.resource_get_with_faulty_put = GetWithFaultyPutResource()
        self.api.add_route('/get_with_param/{param}',
                           self.resource_get_with_faulty_put)

    def test_get(self):
        self.simulate_request('/things/42/stuff/57')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertTrue(self.resource_things.called)

    def test_put(self):
        self.simulate_request('/things/42/stuff/1337', method='PUT')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertTrue(self.resource_things.called)

    def test_post_not_allowed(self):
        self.simulate_request('/things/42/stuff/1337', method='POST')
        self.assertEqual(self.srmock.status, falcon.HTTP_405)
        self.assertFalse(self.resource_things.called)

    def test_misc(self):
        for method in ['GET', 'HEAD', 'PUT', 'PATCH']:
            self.resource_misc.called = False
            self.simulate_request('/misc', method=method)
            self.assertTrue(self.resource_misc.called)
            self.assertEqual(self.resource_misc.req.method, method)

    def test_methods_not_allowed_simple(self):
        for method in ['GET', 'HEAD', 'PUT', 'PATCH']:
            self.simulate_request('/stonewall', method=method)
            self.assertEqual(self.srmock.status, falcon.HTTP_405)

    def test_methods_not_allowed_complex(self):
        for method in HTTP_METHODS:
            if method in ('GET', 'PUT', 'HEAD', 'OPTIONS'):
                continue

            self.resource_things.called = False
            self.simulate_request('/things/84/stuff/65', method=method)

            self.assertFalse(self.resource_things.called)
            self.assertEqual(self.srmock.status, falcon.HTTP_405)

            headers = self.srmock.headers
            allow_header = ('allow', 'GET, HEAD, PUT, OPTIONS')

            self.assertThat(headers, Contains(allow_header))

    def test_method_not_allowed_with_param(self):
        for method in HTTP_METHODS:
            if method in ('GET', 'PUT', 'OPTIONS'):
                continue

            self.resource_get_with_faulty_put.called = False
            self.simulate_request(
                '/get_with_param/bogus_param', method=method)

            self.assertFalse(self.resource_get_with_faulty_put.called)
            self.assertEqual(self.srmock.status, falcon.HTTP_405)

            headers = self.srmock.headers
            allow_header = ('allow', 'GET, PUT, OPTIONS')

            self.assertThat(headers, Contains(allow_header))

    def test_default_on_options(self):
        self.simulate_request('/things/84/stuff/65', method='OPTIONS')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        headers = self.srmock.headers
        allow_header = ('allow', 'GET, HEAD, PUT')

        self.assertThat(headers, Contains(allow_header))

    def test_bogus_method(self):
        self.simulate_request('/things', method=self.getUniqueString())
        self.assertFalse(self.resource_things.called)
        self.assertEqual(self.srmock.status, falcon.HTTP_400)
