import falcon
import falcon.testing as testing


def capture_error(e, req, resp, params):
    resp.status = falcon.HTTP_723
    resp.body = 'error: %s' % str(e)


def handle_error_first(e, req, resp, params):
    resp.status = falcon.HTTP_200
    resp.body = 'first error handler'


class CustomBaseException(Exception):
    pass


class CustomException(CustomBaseException):
    pass


class ErroredClassResource(object):
    def on_get(self, req, resp):
        raise Exception('Plain Exception')

    def on_head(self, req, resp):
        raise CustomBaseException('CustomBaseException')

    def on_delete(self, req, resp):
        raise CustomException('CustomException')


class TestErrorHandler(testing.TestBase):

    def before(self):
        self.resource = ErroredClassResource()
        self.api.add_route(self.test_route, self.resource)

    def test_caught_error(self):
        self.api = falcon.API()
        self.api.add_error_handler(Exception, capture_error)

        self.api.add_route(self.test_route, ErroredClassResource())

        body = self.simulate_request(self.test_route)
        self.assertEqual([b'error: Plain Exception'], body)

        body = self.simulate_request(self.test_route, method='HEAD')
        self.assertEqual(falcon.HTTP_723, self.srmock.status)
        self.assertEqual([], body)

    def test_uncaught_error(self):
        self.api = falcon.API()
        self.api.add_error_handler(CustomException, capture_error)

        self.api.add_route(self.test_route, ErroredClassResource())

        self.assertRaises(Exception,
                          self.simulate_request, self.test_route)

    def test_subclass_error(self):
        self.api = falcon.API()
        self.api.add_error_handler(CustomBaseException, capture_error)

        self.api.add_route(self.test_route, ErroredClassResource())

        body = self.simulate_request(self.test_route, method='DELETE')
        self.assertEqual(falcon.HTTP_723, self.srmock.status)
        self.assertEqual([b'error: CustomException'], body)

    def test_error_order(self):
        self.api = falcon.API()

        self.api.add_error_handler(Exception, capture_error)
        self.api.add_error_handler(Exception, handle_error_first)

        self.api.add_route(self.test_route, ErroredClassResource())

        body = self.simulate_request(self.test_route)
        self.assertEqual([b'first error handler'], body)
