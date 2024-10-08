import multiprocessing
import os
import os.path
import time
from wsgiref.simple_server import make_server

import pytest

import falcon
import falcon.testing as testing

_HERE = os.path.abspath(os.path.dirname(__file__))
_SERVER_HOST = 'localhost'
_SERVER_PORT = 9800 + os.getpid() % 100  # Facilitates parallel test execution
_SERVER_BASE_URL = 'http://{}:{}/'.format(_SERVER_HOST, _SERVER_PORT)
_SIZE_1_KB = 1024


@pytest.mark.usefixtures('_setup_wsgi_server')
class TestWSGIServer:
    def test_get(self, requests_lite):
        resp = requests_lite.get(_SERVER_BASE_URL)
        assert resp.status_code == 200
        assert resp.text == '127.0.0.1'

    def test_get_file(self, requests_lite):
        # NOTE(vytas): There was a breaking change in the behaviour of
        #   ntpath.isabs() in CPython 3.13, let us verify basic file serving.
        resp = requests_lite.get(_SERVER_BASE_URL + 'tests/test_wsgi.py')
        assert resp.status_code == 200
        assert 'class TestWSGIServer:' in resp.text

    def test_put(self, requests_lite):
        body = '{}'
        resp = requests_lite.put(_SERVER_BASE_URL, data=body)
        assert resp.status_code == 200
        assert resp.text == '{}'

    def test_head_405(self, requests_lite):
        body = '{}'
        resp = requests_lite.head(_SERVER_BASE_URL, data=body)
        assert resp.status_code == 405

    def test_post(self, requests_lite):
        body = testing.rand_string(_SIZE_1_KB // 2, _SIZE_1_KB)
        resp = requests_lite.post(_SERVER_BASE_URL, data=body)
        assert resp.status_code == 200
        assert resp.text == body

    def test_post_invalid_content_length(self, requests_lite):
        headers = {'Content-Length': 'invalid'}
        resp = requests_lite.post(_SERVER_BASE_URL, headers=headers)
        assert resp.status_code == 400

    def test_post_read_bounded_stream(self, requests_lite):
        body = testing.rand_string(_SIZE_1_KB // 2, _SIZE_1_KB)
        resp = requests_lite.post(_SERVER_BASE_URL + 'bucket', data=body)
        assert resp.status_code == 200
        assert resp.text == body

    def test_post_read_bounded_stream_no_body(self, requests_lite):
        resp = requests_lite.post(_SERVER_BASE_URL + 'bucket')
        assert not resp.text


def _run_server(stop_event, host, port):
    class Things:
        def on_get(self, req, resp):
            resp.text = req.remote_addr

        def on_post(self, req, resp):
            # NOTE(kgriffs): Elsewhere we just use req.bounded_stream, so
            # here we read the stream directly to test that use case.
            resp.text = req.stream.read(req.content_length or 0)

        def on_put(self, req, resp):
            # NOTE(kgriffs): Test that reading past the end does
            # not hang.
            req_body = (
                req.bounded_stream.read(1) for i in range(req.content_length + 1)
            )

            resp.text = b''.join(req_body)

    class Bucket:
        def on_post(self, req, resp):
            # NOTE(kgriffs): This would normally block when
            # Content-Length is 0 and the WSGI input object.
            # BoundedStream fixes that. This is just a sanity check to
            # make sure req.bounded_stream is what we think it is;
            # BoundedStream itself has its own unit tests in
            # test_request_body.py
            resp.text = req.bounded_stream.read()

            # NOTE(kgriffs): No need to also test the same read() for
            # req.stream, since we already asserted they are the same
            # objects.

    api = application = falcon.App()
    api.add_route('/', Things())
    api.add_route('/bucket', Bucket())
    api.add_static_route('/tests', _HERE)

    server = make_server(host, port, application)

    while not stop_event.is_set():
        server.handle_request()


@pytest.fixture(scope='module')
def _setup_wsgi_server(requests_lite):
    stop_event = multiprocessing.Event()
    process = multiprocessing.Process(
        target=_run_server,
        daemon=True,
        # NOTE(kgriffs): Pass these explicitly since if multiprocessing is
        #   using the 'spawn' start method, we can't depend on closures.
        args=(stop_event, _SERVER_HOST, _SERVER_PORT),
    )

    process.start()

    # NOTE(vytas): Give the server some time to start.
    for attempt in range(3):
        try:
            requests_lite.get(_SERVER_BASE_URL, timeout=1)
            break
        except OSError:
            pass

        time.sleep(attempt + 0.2)

    yield

    stop_event.set()

    # NOTE(kgriffs): Pump the request handler loop in case execution
    # made it to the next server.handle_request() before we sent the
    # event.
    try:
        requests_lite.get(_SERVER_BASE_URL)
    except OSError:
        pass  # Process already exited

    process.join()
