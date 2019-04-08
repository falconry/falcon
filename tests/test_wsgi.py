import multiprocessing
import os
import time
from wsgiref.simple_server import make_server

import pytest
import requests

import falcon
import falcon.testing as testing

_SERVER_HOST = 'localhost'
_SERVER_PORT = 9800 + os.getpid() % 100  # Facilitates parallel test execution
_SERVER_BASE_URL = 'http://{}:{}/'.format(_SERVER_HOST, _SERVER_PORT)
_SIZE_1_KB = 1024


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
        assert resp.status_code == 400

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
            # NOTE(kgriffs): Elsewhere we just use req.bounded_stream, so
            # here we read the stream directly to test that use case.
            resp.body = req.stream.read(req.content_length or 0)

        def on_put(self, req, resp):
            # NOTE(kgriffs): Test that reading past the end does
            # not hang.
            req_body = (req.bounded_stream.read(1)
                        for i in range(req.content_length + 1))

            resp.body = b''.join(req_body)

    class Bucket(object):
        def on_post(self, req, resp):
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
        pass  # Process already exited

    process.join()
