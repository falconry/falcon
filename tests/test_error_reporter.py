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


def _error_handler(asgi, handler):
    if not asgi:
        return handler

    async def handler_async(req, resp, ex, params):
        handler(req, resp, ex, params)

    return handler_async


@pytest.fixture()
def reporter(asgi, util):
    class InternetPageMiddleware:
        def process_request(self, req, resp):
            if req.path == '/last-page':
                raise falcon.HTTPStatus(falcon.HTTP_797)

        async def process_request_async(self, req, resp):
            self.process_request(req, resp)

    class Inverse:
        def on_get(self, req, resp, number):
            resp.media = {'result': 1 / number}

    class InverseAsync:
        async def on_get(self, req, resp, number):
            resp.media = {'result': 1 / number}

    resource_type = (
        falcon.testing.SimpleTestResourceAsync
        if asgi
        else falcon.testing.SimpleTestResource
    )

    app = util.create_app(asgi)
    app.add_middleware(InternetPageMiddleware())
    app.add_route('/inverse/{number:float}', InverseAsync() if asgi else Inverse())
    app.add_route('/resource', resource_type(json={'message': 'Hello'}))
    client = falcon.testing.TestClient(app)

    error_reporter = ErrorReporter(client)
    app.set_error_reporter(error_reporter.report)

    return error_reporter


@pytest.fixture()
def client(reporter):
    return reporter.client


@pytest.fixture()
def wsgierrors():
    # NOTE(vytas): Falcon does not log the exceptions it bubbles up to the app
    #   server; this stream is used to check what the framework logged itself.
    #   (wsgierrors is unused with ASGI, but passing it is harmless.)
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
    # NOTE(vytas): Normally, there is no straightforward way to remove the
    #   default Exception handler, so we have to operate on a private variable.
    client.app._error_handlers.pop(Exception)

    with pytest.raises(ZeroDivisionError):
        client.get('/inverse/0.0')

    assert reporter.log == [(ZeroDivisionError, False)]


def test_handler_reraises(asgi, client, reporter):
    def bubble_up(req, resp, ex, params):
        raise

    client.app.add_error_handler(Exception, _error_handler(asgi, bubble_up))

    with pytest.raises(ZeroDivisionError):
        client.get('/inverse/0.0')

    assert reporter.log == [(ZeroDivisionError, False)]


def test_handler_reraises_http_error(asgi, client, reporter):
    def bubble_up(req, resp, ex, params):
        raise

    client.app.add_error_handler(falcon.HTTPError, _error_handler(asgi, bubble_up))

    resp = client.get('/404')
    assert resp.status_code == 404
    assert reporter.log == [(falcon.HTTPRouteNotFound, True)]


def test_handler_raises_http_status(asgi, client, reporter):
    def handle_zero_division(req, resp, ex, params):
        raise falcon.HTTPStatus(falcon.HTTP_OK, text='{"result": null}')

    client.app.add_error_handler(
        ZeroDivisionError, _error_handler(asgi, handle_zero_division)
    )

    resp = client.get('/inverse/0.0')
    assert resp.status_code == 200
    assert resp.json == {'result': None}
    assert reporter.log == [(ZeroDivisionError, True), (falcon.HTTPStatus, True)]


def test_handler_raises_http_error(asgi, client, reporter):
    def handle_zero_division(req, resp, ex, params):
        raise falcon.HTTPUnprocessableEntity(description=str(ex))

    client.app.add_error_handler(
        ZeroDivisionError, _error_handler(asgi, handle_zero_division)
    )

    resp = client.get('/inverse/0.0')
    assert resp.status_code == 422
    assert reporter.log == [
        (ZeroDivisionError, True),
        (falcon.HTTPUnprocessableEntity, True),
    ]


@pytest.mark.parametrize('set_reporter', (True, False))
def test_handler_raises_exception(asgi, util, reporter, wsgierrors, set_reporter):
    class Inverse:
        def on_get(self, req, resp):
            1 / 0

    class InverseAsync:
        async def on_get(self, req, resp):
            1 / 0

    def handle_error(req, resp, ex, params):
        raise RuntimeError(f'application error: {ex}')

    app = util.create_app(asgi)
    app.add_route('/inverse', InverseAsync() if asgi else Inverse())
    app.add_error_handler(ZeroDivisionError, _error_handler(asgi, handle_error))
    if set_reporter:
        app.set_error_reporter(reporter.report)

    with pytest.raises(RuntimeError):
        falcon.testing.simulate_get(app, '/inverse', wsgierrors=wsgierrors)

    assert reporter.log == (
        [(ZeroDivisionError, False), (RuntimeError, False)] if set_reporter else []
    )
    # NOTE(vytas): The RuntimeError is left for the app server to handle.
    assert wsgierrors.getvalue() == ''


@pytest.mark.parametrize('set_reporter', (True, False))
def test_serializer_raises(asgi, util, reporter, wsgierrors, set_reporter):
    class Inverse:
        def on_get(self, req, resp):
            1 / 0

    class InverseAsync:
        async def on_get(self, req, resp):
            1 / 0

    def handle_zero_division(req, resp, ex, params):
        raise falcon.HTTPUnprocessableEntity(description=str(ex))

    def serialize_error(req, resp, exception):
        raise RuntimeError('serializer error')

    app = util.create_app(asgi)
    app.add_route('/inverse', InverseAsync() if asgi else Inverse())
    app.add_error_handler(ZeroDivisionError, _error_handler(asgi, handle_zero_division))
    app.set_error_serializer(serialize_error)
    if set_reporter:
        app.set_error_reporter(reporter.report)

    with pytest.raises(RuntimeError):
        falcon.testing.simulate_get(app, '/inverse', wsgierrors=wsgierrors)

    # NOTE(vytas): Every exception is reported exactly once: the original
    #   error, the derived HTTPError, and the error from the serializer itself.
    assert reporter.log == (
        [
            (ZeroDivisionError, False),
            (falcon.HTTPUnprocessableEntity, False),
            (RuntimeError, False),
        ]
        if set_reporter
        else []
    )
    assert wsgierrors.getvalue() == ''


@pytest.mark.parametrize('set_reporter', (True, False))
def test_report_fatal_error_starting_resp(
    asgi, util, reporter, wsgierrors, set_reporter
):
    class StrangeMiddleware:
        def process_response(self, req, resp, rsrc, succeeded):
            resp.status = object()

        async def process_response_async(self, req, resp, rsrc, succeeded):
            self.process_response(req, resp, rsrc, succeeded)

    app = util.create_app(asgi)
    app.add_middleware(StrangeMiddleware())
    if set_reporter:
        app.set_error_reporter(reporter.report)

    with pytest.raises(ValueError):
        falcon.testing.simulate_get(app, '/', wsgierrors=wsgierrors)

    assert reporter.log == (
        [(falcon.HTTPRouteNotFound, True), (ValueError, False)] if set_reporter else []
    )
    # NOTE(vytas): The ValueError is left for the app server to handle.
    assert wsgierrors.getvalue() == ''


@pytest.mark.parametrize('status', (falcon.HTTP_200, falcon.HTTP_204))
@pytest.mark.parametrize('set_reporter', (True, False))
def test_report_fatal_error_rendering_asgi_headers(util, status, set_reporter):
    # NOTE(vytas): Unlike WSGI, where headers are passed to the app server as
    #   native strings, ASGI headers are encoded by the framework itself.
    resource = falcon.testing.SimpleTestResourceAsync(
        status=status, body='Hello', headers={'X-Falcon': '🦅'}
    )
    reporter = ErrorReporter(None)

    app = util.create_app(True)
    app.add_route('/', resource)
    if set_reporter:
        app.set_error_reporter(reporter.report)

    with pytest.raises(ValueError):
        falcon.testing.simulate_get(app, '/')

    assert reporter.log == ([(ValueError, False)] if set_reporter else [])


async def test_report_websocket(util):
    class Chat:
        async def on_websocket(self, req, ws):
            await ws.accept()
            await ws.send_text(f'Your score: {1 / 0}')

    reporter = ErrorReporter(None)

    app = util.create_app(True)
    app.add_route('/chat', Chat())
    app.set_error_reporter(reporter.report)

    async with falcon.testing.ASGIConductor(app) as conductor:
        async with conductor.simulate_ws('/chat') as ws:
            with pytest.raises(falcon.WebSocketDisconnected):
                await ws.receive_text()

    assert reporter.log == [(ZeroDivisionError, True)]
