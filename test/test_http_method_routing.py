import helpers
import falcon

from testtools.matchers import Contains

HTTP_METHODS = (
    'CONNECT',
    'DELETE',
    'GET',
    'HEAD',
    'OPTIONS',
    'POST',
    'PUT',
    'TRACE'
)


class RequestHandlerWithGet:
    def __init__(self):
        self.called = False

    def on_get(self, ctx, req, resp):
        self.called = True

        self.ctx, self.req, self.resp = ctx, req, resp
        resp.status = falcon.HTTP_200


class RequestHandlerMisc:
    def __init__(self):
        self.called = False

    def on_get(self, ctx, req, resp):
        self.called = True

        self.ctx, self.req, self.resp = ctx, req, resp
        resp.status = falcon.HTTP_204

    def on_head(self, ctx, req, resp):
        self.called = True

        self.ctx, self.req, self.resp = ctx, req, resp
        resp.status = falcon.HTTP_204

    def on_put(self, ctx, req, resp):
        self.called = True

        self.ctx, self.req, self.resp = ctx, req, resp
        resp.status = falcon.HTTP_400


class TestHttpMethodRouting(helpers.TestSuite):

    def prepare(self):
        self.reqhandler_get = RequestHandlerWithGet()
        self.api.add_route('/get', self.reqhandler_get)

        self.reqhandler_misc = RequestHandlerMisc()
        self.api.add_route('/misc', self.reqhandler_misc)

    def test_get(self):
        self._simulate_request('/get')
        self.assertTrue(self.reqhandler_get.called)

    def test_misc(self):
        for method in ['GET', 'HEAD', 'PUT']:
            self.reqhandler_misc.called = False
            self._simulate_request('/misc', method=method)
            self.assertTrue(self.reqhandler_misc.called)
            self.assertEquals(self.reqhandler_misc.req.method, method)

    def test_method_not_allowed(self):
        for method in HTTP_METHODS:
            if method == 'GET':
                continue

            self.reqhandler_get.called = False
            self._simulate_request('/get', method=method)

            self.assertFalse(self.reqhandler_get.called)
            self.assertEquals(self.srmock.status, '405 Method Not Allowed')

            headers = self.srmock.headers
            allow_header = ('Allow', 'GET')

            self.assertThat(headers, Contains(allow_header))

    def test_bogus_method(self):
        self._simulate_request('/get', method=self.getUniqueString())
        self.assertFalse(self.reqhandler_get.called)
