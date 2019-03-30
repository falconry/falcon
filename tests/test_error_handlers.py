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


@pytest.fixture
def client():
    app = falcon.API()
    app.add_route('/', ErroredClassResource())
    return testing.TestClient(app)


class TestErrorHandler(object):

    def test_caught_error(self, client):
        client.app.add_error_handler(Exception, capture_error)

        result = client.simulate_get()
        assert result.text == 'error: Plain Exception'

        result = client.simulate_head()
        assert result.status_code == 723
        assert not result.content

    def test_uncaught_error(self, client):
        client.app.add_error_handler(CustomException, capture_error)
        with pytest.raises(Exception):
            client.simulate_get()

    def test_uncaught_error_else(self, client):
        with pytest.raises(Exception):
            client.simulate_get()

    def test_converted_error(self, client):
        client.app.add_error_handler(CustomException)

        result = client.simulate_delete()
        assert result.status_code == 792
        assert result.json[u'title'] == u'Internet crashed!'

    def test_handle_not_defined(self, client):
        with pytest.raises(AttributeError):
            client.app.add_error_handler(CustomBaseException)

    def test_subclass_error(self, client):
        client.app.add_error_handler(CustomBaseException, capture_error)

        result = client.simulate_delete()
        assert result.status_code == 723
        assert result.text == 'error: CustomException'

    def test_error_order_duplicate(self, client):
        client.app.add_error_handler(Exception, capture_error)
        client.app.add_error_handler(Exception, handle_error_first)

        result = client.simulate_get()
        assert result.text == 'first error handler'

    def test_error_order_subclass(self, client):
        client.app.add_error_handler(Exception, capture_error)
        client.app.add_error_handler(CustomException, handle_error_first)

        result = client.simulate_delete()
        assert result.status_code == 200
        assert result.text == 'first error handler'

        result = client.simulate_get()
        assert result.status_code == 723
        assert result.text == 'error: Plain Exception'

    def test_error_order_subclass_masked(self, client):
        client.app.add_error_handler(CustomException, handle_error_first)
        client.app.add_error_handler(Exception, capture_error)

        result = client.simulate_delete()
        assert result.status_code == 723
        assert result.text == 'error: CustomException'

    @pytest.mark.parametrize('exceptions', [
        (Exception, CustomException),
        [Exception, CustomException],
    ])
    def test_handler_multiple_exception_iterable(self, client, exceptions):
        client.app.add_error_handler(exceptions, capture_error)

        result = client.simulate_get()
        assert result.status_code == 723

        result = client.simulate_delete()
        assert result.status_code == 723

    def test_handler_single_exception_iterable(self, client):
        def exception_list_generator():
            yield CustomException

        client.app.add_error_handler(exception_list_generator(), capture_error)

        result = client.simulate_delete()
        assert result.status_code == 723

    @pytest.mark.parametrize('exceptions', [
        NotImplemented,
        'Hello, world!',
        frozenset([ZeroDivisionError, int, NotImplementedError]),
        iter([float, float]),
    ])
    def test_invalid_add_exception_handler_input(self, client, exceptions):
        with pytest.raises(TypeError):
            client.app.add_error_handler(exceptions, capture_error)

    def test_handler_signature_shim(self, client):
        def check_args(ex, req, resp):
            assert isinstance(ex, BaseException)
            assert isinstance(req, falcon.Request)
            assert isinstance(resp, falcon.Response)

        def legacy_handler1(ex, req, resp, params):
            check_args(ex, req, resp)

        def legacy_handler2(error_obj, request, response, params):
            check_args(error_obj, request, response)

        def legacy_handler3(err, rq, rs, prms):
            check_args(err, rq, rs)

        client.app.add_error_handler(Exception, legacy_handler1)
        client.app.add_error_handler(CustomBaseException, legacy_handler2)
        client.app.add_error_handler(CustomException, legacy_handler3)

        client.simulate_delete()
        client.simulate_get()
        client.simulate_head()
