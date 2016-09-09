import sys
import time
from wsgiref.simple_server import make_server

try:
    import multiprocessing
except ImportError:
    pass  # Jython

import pytest
import requests

import falcon
from falcon.request_helpers import BoundedStream
import falcon.testing as testing

_SERVER_HOST = 'localhost'
_SERVER_PORT = 9809
_SERVER_BASE_URL = 'http://{0}:{1}/'.format(_SERVER_HOST, _SERVER_PORT)
_SIZE_1_KB = 1024


@pytest.mark.skipif(
    # NOTE(kgriffs): Jython does not support the multiprocessing
    # module. We could alternatively implement these tests
    # using threads, but then we have to force a garbage
    # collection in between each test in order to make
    # the server relinquish its socket, and the gc module
    # doesn't appear to do anything under Jython.

    'java' in sys.platform,
    reason='Incompatible with Jython'
)
@pytest.mark.usefixtures('_setup_wsgi_server')
class TestWSGIServer(object):

    def test_get(self):
        resp = requests.get(_SERVER_BASE_URL)
        assert resp.status_code == 200
        assert resp.text == '127.0.0.1'

    def test_put(self):
        body = '{}'
        resp = requests.put(_SERVER_BASE_URL, data=body)
        assert resp.status_code == 200
        assert resp.text == '{}'

    def test_head_405(self):
        body = '{}'
        resp = requests.head(_SERVER_BASE_URL, data=body)
        assert resp.status_code == 405

    def test_post(self):
        body = testing.rand_string(_SIZE_1_KB / 2, _SIZE_1_KB)
        resp = requests.post(_SERVER_BASE_URL, data=body)
        assert resp.status_code == 200
        assert resp.text == body

    def test_post_invalid_content_length(self):
        headers = {'Content-Length': 'invalid'}
        resp = requests.post(_SERVER_BASE_URL, headers=headers)
        assert resp.status_code == 200
        assert resp.text == ''

    def test_post_read_bounded_stream(self):
        body = testing.rand_string(_SIZE_1_KB / 2, _SIZE_1_KB)
        resp = requests.post(_SERVER_BASE_URL + 'bucket', data=body)
        assert resp.status_code == 200
        assert resp.text == body

    def test_post_read_bounded_stream_no_body(self):
        resp = requests.post(_SERVER_BASE_URL + 'bucket')
        assert not resp.text


def _run_server(stop_event):
    class Things(object):
        def on_get(self, req, resp):
            resp.body = req.remote_addr

        def on_post(self, req, resp):
            resp.body = req.stream.read(_SIZE_1_KB)

        def on_put(self, req, resp):
            # NOTE(kgriffs): Test that reading past the end does
            # not hang.
            req_body = (req.stream.read(1)
                        for i in range(req.content_length + 1))

            resp.body = b''.join(req_body)

    class Bucket(object):
        def on_post(self, req, resp):
            # NOTE(kgriffs): The framework automatically detects
            # wsgiref's input object type and wraps it; we'll probably
            # do away with this at some point, but for now we
            # verify the functionality,
            assert isinstance(req.stream, BoundedStream)

            # NOTE(kgriffs): Ensure we are reusing the same object for
            # the sake of efficiency and to ensure a shared state of the
            # stream. (only in the case that we have decided to
            # automatically wrap the WSGI input object, i.e. when
            # running under wsgiref or similar).
            assert req.stream is req.bounded_stream

            # NOTE(kgriffs): This would normally block when
            # Content-Length is 0 and the WSGI input object.
            # BoundedStream fixes that. This is just a sanity check to
            # make sure req.bounded_stream is what we think it is;
            # BoundedStream itself has its own unit tests in
            # test_request_body.py
            resp.body = req.bounded_stream.read()

            # NOTE(kgriffs): No need to also test the same read() for
            # req.stream, since we already asserted they are the same
            # objects.

    api = application = falcon.API()
    api.add_route('/', Things())
    api.add_route('/bucket', Bucket())

    server = make_server(_SERVER_HOST, _SERVER_PORT, application)

    while not stop_event.is_set():
        server.handle_request()


@pytest.fixture
def _setup_wsgi_server():
    stop_event = multiprocessing.Event()
    process = multiprocessing.Process(
        target=_run_server,
        args=(stop_event,)
    )

    process.start()

    # NOTE(kgriffs): Let the server start up
    time.sleep(0.2)

    yield

    stop_event.set()

    # NOTE(kgriffs): Pump the request handler loop in case execution
    # made it to the next server.handle_request() before we sent the
    # event.
    try:
        requests.get(_SERVER_BASE_URL)
    except Exception:
        pass  # Thread already exited

    process.join()
