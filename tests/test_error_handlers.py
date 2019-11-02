import pytest

import falcon
from falcon import constants, testing


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
            'Internet crashed!',
            'Catastrophic weather event',
            href='http://example.com/api/inconvenient-truth',
            href_text='Drill, baby drill!')


class ErroredClassResource:

    def on_get(self, req, resp):
        raise Exception('Plain Exception')

    def on_head(self, req, resp):
        raise CustomBaseException('CustomBaseException')

    def on_delete(self, req, resp):
        raise CustomException('CustomException')


@pytest.fixture
def client():
    app = falcon.App()
    app.add_route('/', ErroredClassResource())
    return testing.TestClient(app)


class TestErrorHandler:

    def test_caught_error(self, client):
        client.app.add_error_handler(Exception, capture_error)

        result = client.simulate_get()
        assert result.text == 'error: Plain Exception'

        result = client.simulate_head()
        assert result.status_code == 723
        assert not result.content

    @pytest.mark.parametrize('get_headers, resp_content_type, resp_start', [
        (None, constants.MEDIA_JSON, '{"'),
        ({'accept': constants.MEDIA_JSON}, constants.MEDIA_JSON, '{"'),
        ({'accept': constants.MEDIA_XML}, constants.MEDIA_XML, '<?xml'),
    ])
    def test_uncaught_python_error(self, client,
                                   get_headers, resp_content_type, resp_start):
        result = client.simulate_get(headers=get_headers)
        assert result.status_code == 500
        assert result.headers['content-type'] == resp_content_type
        assert result.text.startswith(resp_start)

    def test_converted_error(self, client):
        client.app.add_error_handler(CustomException)

        result = client.simulate_delete()
        assert result.status_code == 792
        assert result.json['title'] == 'Internet crashed!'

    def test_handle_not_defined(self, client):
        with pytest.raises(AttributeError):
            client.app.add_error_handler(CustomBaseException)

    def test_subclass_error(self, client):
        client.app.add_error_handler(CustomBaseException, capture_error)

        result = client.simulate_delete()
        assert result.status_code == 723
        assert result.text == 'error: CustomException'

    def test_error_precedence_duplicate(self, client):
        client.app.add_error_handler(Exception, capture_error)
        client.app.add_error_handler(Exception, handle_error_first)

        result = client.simulate_get()
        assert result.text == 'first error handler'

    def test_error_precedence_subclass(self, client):
        client.app.add_error_handler(Exception, capture_error)
        client.app.add_error_handler(CustomException, handle_error_first)

        result = client.simulate_delete()
        assert result.status_code == 200
        assert result.text == 'first error handler'

        result = client.simulate_get()
        assert result.status_code == 723
        assert result.text == 'error: Plain Exception'

    def test_error_precedence_subclass_order_indifference(self, client):
        client.app.add_error_handler(CustomException, handle_error_first)
        client.app.add_error_handler(Exception, capture_error)

        result = client.simulate_delete()
        assert result.status_code == 200
        assert result.text == 'first error handler'

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
