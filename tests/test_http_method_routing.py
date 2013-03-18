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


class ResourceGet(object):
    def __init__(self):
        self.called = False

    def on_get(self, req, resp):
        self.called = True

        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_204


def capture(func):
    @wraps(func)
    def with_capture(*args, **kwargs):
        self = args[0]
        self.called = True
        self.req, self.resp = args[1:]

    return with_capture


class ResourceMisc(object):
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


class ResourceGetWithParam(object):
    def __init__(self):
        self.called = False

    @capture
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_204


class TestHttpMethodRouting(testing.TestBase):

    def before(self):
        self.resource_get = ResourceGet()
        self.api.add_route('/get', self.resource_get)

        self.resource_misc = ResourceMisc()
        self.api.add_route('/misc', self.resource_misc)

        self.resource_get_with_param = ResourceGetWithParam()
        self.api.add_route('/get_with_param/{param}',
                           self.resource_get_with_param)

    def test_get(self):
        self.simulate_request('/get')
        self.assertTrue(self.resource_get.called)

    def test_misc(self):
        for method in ['GET', 'HEAD', 'PUT', 'PATCH']:
            self.resource_misc.called = False
            self.simulate_request('/misc', method=method)
            self.assertTrue(self.resource_misc.called)
            self.assertEquals(self.resource_misc.req.method, method)

    def test_method_not_allowed(self):
        for method in HTTP_METHODS:
            if method == 'GET':
                continue

            self.resource_get.called = False
            self.simulate_request('/get', method=method)

            self.assertFalse(self.resource_get.called)
            self.assertEquals(self.srmock.status, '405 Method Not Allowed')

            headers = self.srmock.headers
            allow_header = ('Allow', 'GET')

            self.assertThat(headers, Contains(allow_header))

    def test_method_not_allowed_with_param(self):
        for method in HTTP_METHODS:
            if method == 'GET':
                continue

            self.resource_get_with_param.called = False
            self.simulate_request(
                '/get_with_param/bogus_param', method=method)

            self.assertFalse(self.resource_get_with_param.called)
            self.assertEquals(self.srmock.status, '405 Method Not Allowed')

            headers = self.srmock.headers
            allow_header = ('Allow', 'GET')

            self.assertThat(headers, Contains(allow_header))

    def test_bogus_method(self):
        self.simulate_request('/get', method=self.getUniqueString())
        self.assertFalse(self.resource_get.called)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)
