import json

import falcon
import falcon.testing as testing


def capture_error(ex, req, resp, params):
    resp.status = falcon.HTTP_723
    resp.body = 'error: %s' % str(ex)


def handle_error_first(ex, req, resp, params):
    resp.status = falcon.HTTP_200
    resp.body = 'first error handler'


class CustomBaseException(Exception):
    pass


class CustomException(CustomBaseException):

    @staticmethod
    def handle(ex, req, resp, params):
        raise falcon.HTTPError(
            falcon.HTTP_792,
            u'Internet crashed!',
            u'Catastrophic weather event',
            href=u'http://example.com/api/inconvenient-truth',
            href_text=u'Drill, baby drill!')


class ErroredClassResource(object):
    def on_get(self, req, resp):
        raise Exception('Plain Exception')

    def on_head(self, req, resp):
        raise CustomBaseException('CustomBaseException')

    def on_delete(self, req, resp):
        raise CustomException('CustomException')


class TestErrorHandler(testing.TestBase):

    def test_caught_error(self):
        self.api.add_error_handler(Exception, capture_error)

        self.api.add_route(self.test_route, ErroredClassResource())

        body = self.simulate_request(self.test_route)
        self.assertEqual([b'error: Plain Exception'], body)

        body = self.simulate_request(self.test_route, method='HEAD')
        self.assertEqual(falcon.HTTP_723, self.srmock.status)
        self.assertEqual([], body)

    def test_uncaught_error(self):
        self.api.add_error_handler(CustomException, capture_error)

        self.api.add_route(self.test_route, ErroredClassResource())

        self.assertRaises(Exception,
                          self.simulate_request, self.test_route)

    def test_uncaught_error_else(self):
        self.api.add_route(self.test_route, ErroredClassResource())

        self.assertRaises(Exception,
                          self.simulate_request, self.test_route)

    def test_converted_error(self):
        self.api.add_error_handler(CustomException)

        self.api.add_route(self.test_route, ErroredClassResource())

        body = self.simulate_request(self.test_route, method='DELETE')
        self.assertEqual(falcon.HTTP_792, self.srmock.status)

        info = json.loads(body[0].decode())
        self.assertEqual('Internet crashed!', info['title'])

    def test_handle_not_defined(self):
        self.assertRaises(AttributeError,
                          self.api.add_error_handler, CustomBaseException)

    def test_subclass_error(self):
        self.api.add_error_handler(CustomBaseException, capture_error)

        self.api.add_route(self.test_route, ErroredClassResource())

        body = self.simulate_request(self.test_route, method='DELETE')
        self.assertEqual(falcon.HTTP_723, self.srmock.status)
        self.assertEqual([b'error: CustomException'], body)

    def test_error_order(self):
        self.api.add_error_handler(Exception, capture_error)
        self.api.add_error_handler(Exception, handle_error_first)

        self.api.add_route(self.test_route, ErroredClassResource())

        body = self.simulate_request(self.test_route)
        self.assertEqual([b'first error handler'], body)
