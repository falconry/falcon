import pytest

import falcon
from falcon import testing


def capture_error(req, resp, ex, params):
    resp.status = falcon.HTTP_723
    resp.body = 'error: %s' % str(ex)


def handle_error_first(req, resp, ex, params):
    resp.status = falcon.HTTP_200
    resp.body = 'first error handler'


class CustomBaseException(Exception):
    pass


class CustomException(CustomBaseException):

    @staticmethod
    def handle(req, resp, ex, params):
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


class TestErrorHandler(object):

    def test_caught_error(self):
        resource = ErroredClassResource()
        app = falcon.APIBuilder() \
            .add_head_route('/', resource.on_head) \
            .add_get_route('/', resource.on_get) \
            .add_delete_route('/', resource.on_delete) \
            .add_error_route(Exception, capture_error) \
            .build()

        client = testing.TestClient(app)

        result = client.simulate_get()
        assert result.text == 'error: Plain Exception'

        result = client.simulate_head()
        assert result.status_code == 723
        assert not result.content

    def test_uncaught_error(self):
        resource = ErroredClassResource()
        app = falcon.APIBuilder() \
            .add_head_route('/', resource.on_head) \
            .add_get_route('/', resource.on_get) \
            .add_delete_route('/', resource.on_delete) \
            .add_error_route(CustomException, capture_error) \
            .build()

        client = testing.TestClient(app)

        with pytest.raises(Exception):
            client.simulate_get()

    def test_uncaught_error_else(self):
        resource = ErroredClassResource()
        app = falcon.APIBuilder() \
            .add_head_route('/', resource.on_head) \
            .add_get_route('/', resource.on_get) \
            .add_delete_route('/', resource.on_delete) \
            .build()

        client = testing.TestClient(app)
        with pytest.raises(Exception):
            client.simulate_get()

    def test_converted_error(self):
        resource = ErroredClassResource()
        app = falcon.APIBuilder() \
            .add_head_route('/', resource.on_head) \
            .add_get_route('/', resource.on_get) \
            .add_delete_route('/', resource.on_delete) \
            .add_error_route(CustomException) \
            .build()

        client = testing.TestClient(app)

        result = client.simulate_delete()
        assert result.status_code == 792
        assert result.json[u'title'] == u'Internet crashed!'

    def test_handle_not_defined(self):
        resource = ErroredClassResource()
        app = falcon.APIBuilder() \
            .add_head_route('/', resource.on_head) \
            .add_get_route('/', resource.on_get) \
            .add_delete_route('/', resource.on_delete) \
            .build()

        client = testing.TestClient(app)
        with pytest.raises(AttributeError):
            client.app.add_error_handler(CustomBaseException)

    def test_subclass_error(self):
        resource = ErroredClassResource()
        app = falcon.APIBuilder() \
            .add_head_route('/', resource.on_head) \
            .add_get_route('/', resource.on_get) \
            .add_delete_route('/', resource.on_delete) \
            .add_error_route(CustomBaseException, capture_error) \
            .build()

        client = testing.TestClient(app)

        result = client.simulate_delete()
        assert result.status_code == 723
        assert result.text == 'error: CustomException'

    def test_error_order_duplicate(self):
        resource = ErroredClassResource()
        app = falcon.APIBuilder() \
            .add_head_route('/', resource.on_head) \
            .add_get_route('/', resource.on_get) \
            .add_delete_route('/', resource.on_delete) \
            .add_error_route(Exception, capture_error) \
            .add_error_route(Exception, handle_error_first) \
            .build()

        client = testing.TestClient(app)

        result = client.simulate_get()
        assert result.text == 'first error handler'

    def test_error_order_subclass(self):
        resource = ErroredClassResource()
        app = falcon.APIBuilder() \
            .add_head_route('/', resource.on_head) \
            .add_get_route('/', resource.on_get) \
            .add_delete_route('/', resource.on_delete) \
            .add_error_route(Exception, capture_error) \
            .add_error_route(CustomException, handle_error_first) \
            .build()

        client = testing.TestClient(app)

        result = client.simulate_delete()
        assert result.status_code == 200
        assert result.text == 'first error handler'

        result = client.simulate_get()
        assert result.status_code == 723
        assert result.text == 'error: Plain Exception'

    def test_error_order_subclass_masked(self):
        resource = ErroredClassResource()
        app = falcon.APIBuilder() \
            .add_head_route('/', resource.on_head) \
            .add_get_route('/', resource.on_get) \
            .add_delete_route('/', resource.on_delete) \
            .add_error_route(CustomException, handle_error_first) \
            .add_error_route(Exception, capture_error) \
            .build()

        client = testing.TestClient(app)

        result = client.simulate_delete()
        assert result.status_code == 723
        assert result.text == 'error: CustomException'
