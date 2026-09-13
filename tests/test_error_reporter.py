import io

import pytest

import falcon
import falcon.testing


class ErrorReporter:
    def __init__(self, client):
        self.client = client
        self.log = []

    def report(self, req, ex, params, handled):
        self.log.append((type(ex), handled))


# TODO(vytas): Add the asgi parametrizer when that part lands.
@pytest.fixture()
def reporter(util):
    class InternetPageMiddleware:
        def process_request(self, req, resp):
            if req.path == '/last-page':
                raise falcon.HTTPStatus(falcon.HTTP_797)

        async def process_request_async(self, req, resp):
            self.process_request(req, resp)

    class Inverse:
        def on_get(self, req, resp, number):
            resp.media = {'result': 1 / number}

    app = util.create_app(False)
    app.add_middleware(InternetPageMiddleware())
    app.add_route('/inverse/{number:float}', Inverse())
    app.add_route(
        '/resource', falcon.testing.SimpleTestResource(json={'message': 'Hello'})
    )
    client = falcon.testing.TestClient(app)

    error_reporter = ErrorReporter(client)
    app.set_error_reporter(error_reporter.report)

    return error_reporter


@pytest.fixture()
def client(reporter):
    return reporter.client


@pytest.fixture()
def wsgierrors():
    # NOTE(vytas): Falcon does not log the exceptions it leaves for the WSGI
    #   app server to handle (and log); this stream captures whatever the
    #   framework logs, so that we can assert it stayed empty.
    return io.StringIO()


def test_report_none(client, reporter):
    resp = client.get('/resource')
    assert resp.status_code == 200
    assert reporter.log == []


def test_report_404(client, reporter):
    resp = client.get('/404')
    assert resp.status_code == 404
    assert reporter.log == [(falcon.HTTPRouteNotFound, True)]


def test_report_http_status(client, reporter):
    resp = client.get('/last-page')
    assert resp.status == '797 This is the last page of the Internet. Go back'
    assert reporter.log == [(falcon.HTTPStatus, True)]


def test_handler_not_found(client, reporter):
    # NOTE(vytas): Normally, there is no way to remove the default exception
    #   handler, so we have to operate on a private variable.
    client.app._error_handlers.pop(Exception)

    with pytest.raises(ZeroDivisionError):
        client.get('/inverse/0.0')

    assert reporter.log == [(ZeroDivisionError, False)]


def test_handler_reraises(client, reporter):
    def bubble_up(req, resp, ex, params):
        raise

    client.app.add_error_handler(Exception, bubble_up)

    with pytest.raises(ZeroDivisionError):
        client.get('/inverse/0.0')

    assert reporter.log == [(ZeroDivisionError, True)]


def test_handler_raises_http_status(client, reporter):
    def handle_zero_division(req, resp, ex, params):
        raise falcon.HTTPStatus(falcon.HTTP_OK, text='{"result": null}')

    client.app.add_error_handler(ZeroDivisionError, handle_zero_division)

    resp = client.get('/inverse/0.0')
    assert resp.status_code == 200
    assert resp.json == {'result': None}
    assert reporter.log == [(ZeroDivisionError, True), (falcon.HTTPStatus, True)]


def test_handler_raises_http_error(client, reporter):
    def handle_zero_division(req, resp, ex, params):
        raise falcon.HTTPUnprocessableEntity(description=str(ex))

    client.app.add_error_handler(ZeroDivisionError, handle_zero_division)

    resp = client.get('/inverse/0.0')
    assert resp.status_code == 422
    assert reporter.log == [
        (ZeroDivisionError, True),
        (falcon.HTTPUnprocessableEntity, True),
    ]


@pytest.mark.parametrize('set_reporter', (True, False))
def test_handler_raises_exception(util, reporter, wsgierrors, set_reporter):
    class Inverse:
        def on_get(self, req, resp):
            1 / 0

    def handle_error(req, resp, ex, params):
        raise RuntimeError(f'application error: {ex}')

    app = util.create_app(False)
    app.add_route('/inverse', Inverse())
    app.add_error_handler(ZeroDivisionError, handle_error)
    if set_reporter:
        app.set_error_reporter(reporter.report)

    with pytest.raises(RuntimeError):
        falcon.testing.simulate_get(app, '/inverse', wsgierrors=wsgierrors)

    assert reporter.log == (
        [(ZeroDivisionError, True), (RuntimeError, False)] if set_reporter else []
    )
    # NOTE(vytas): The RuntimeError is left for the WSGI app server to handle.
    assert wsgierrors.getvalue() == ''


@pytest.mark.parametrize('set_reporter', (True, False))
def test_report_fatal_error_starting_resp(util, reporter, wsgierrors, set_reporter):
    class StrangeMiddleware:
        def process_response(self, req, resp, rsrc, succeeded):
            resp.status = object()

        async def process_response_async(self, req, resp, rsrc, succeeded):
            self.process_response(req, resp, rsrc, succeeded)

    app = util.create_app(False)
    app.add_middleware(StrangeMiddleware())
    if set_reporter:
        app.set_error_reporter(reporter.report)

    with pytest.raises(ValueError):
        falcon.testing.simulate_get(app, '/', wsgierrors=wsgierrors)

    assert reporter.log == (
        [(falcon.HTTPRouteNotFound, True), (ValueError, False)] if set_reporter else []
    )
    # NOTE(vytas): The ValueError is left for the WSGI app server to handle.
    assert wsgierrors.getvalue() == ''
