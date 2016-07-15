import falcon
from falcon import testing


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


class TestErrorHandler(testing.TestCase):

    def setUp(self):
        super(TestErrorHandler, self).setUp()
        self.api.add_route('/', ErroredClassResource())

    def test_caught_error(self):
        self.api.add_error_handler(Exception, capture_error)

        result = self.simulate_get()
        self.assertEqual(result.text, 'error: Plain Exception')

        result = self.simulate_head()
        self.assertEqual(result.status_code, 723)
        self.assertFalse(result.content)

    def test_uncaught_error(self):
        self.api.add_error_handler(CustomException, capture_error)
        self.assertRaises(Exception, self.simulate_get)

    def test_uncaught_error_else(self):
        self.assertRaises(Exception, self.simulate_get)

    def test_converted_error(self):
        self.api.add_error_handler(CustomException)

        result = self.simulate_delete()
        self.assertEqual(result.status_code, 792)
        self.assertEqual(result.json[u'title'], u'Internet crashed!')

    def test_handle_not_defined(self):
        self.assertRaises(AttributeError,
                          self.api.add_error_handler, CustomBaseException)

    def test_subclass_error(self):
        self.api.add_error_handler(CustomBaseException, capture_error)

        result = self.simulate_delete()
        self.assertEqual(result.status_code, 723)
        self.assertEqual(result.text, 'error: CustomException')

    def test_error_order_duplicate(self):
        self.api.add_error_handler(Exception, capture_error)
        self.api.add_error_handler(Exception, handle_error_first)

        result = self.simulate_get()
        self.assertEqual(result.text, 'first error handler')

    def test_error_order_subclass(self):
        self.api.add_error_handler(Exception, capture_error)
        self.api.add_error_handler(CustomException, handle_error_first)

        result = self.simulate_delete()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.text, 'first error handler')

        result = self.simulate_get()
        self.assertEqual(result.status_code, 723)
        self.assertEqual(result.text, 'error: Plain Exception')

    def test_error_order_subclass_masked(self):
        self.api.add_error_handler(CustomException, handle_error_first)
        self.api.add_error_handler(Exception, capture_error)

        result = self.simulate_delete()
        self.assertEqual(result.status_code, 723)
        self.assertEqual(result.text, 'error: CustomException')
