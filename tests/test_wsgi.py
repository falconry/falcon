import multiprocessing
import os
import os.path
import platform
import time
import wsgiref.simple_server

import pytest

import falcon
import falcon.testing as testing

_HERE = os.path.abspath(os.path.dirname(__file__))
_SERVER_HOST = 'localhost'
_SIZE_1_KB = 1024
_STARTUP_TIMEOUT = 10
_START_ATTEMPTS = 3


@pytest.mark.skipif(
    platform.system() == 'Darwin',
    reason='Non-deterministic issues with macos-15 GitHub Actions runners',
)
class TestWSGIServer:
    def test_get(self, requests_lite, server_base_url):
        resp = requests_lite.get(server_base_url)
        assert resp.status_code == 200
        assert resp.text == '127.0.0.1'

    def test_get_file(self, requests_lite, server_base_url):
        # NOTE(vytas): There was a breaking change in the behaviour of
        #   ntpath.isabs() in CPython 3.13, let us verify basic file serving.
        resp = requests_lite.get(server_base_url + 'tests/test_wsgi.py')
        assert resp.status_code == 200
        assert 'class TestWSGIServer:' in resp.text

    def test_put(self, requests_lite, server_base_url):
        body = '{}'
        resp = requests_lite.put(server_base_url, data=body)
        assert resp.status_code == 200
        assert resp.text == '{}'

    def test_head_405(self, requests_lite, server_base_url):
        body = '{}'
        resp = requests_lite.head(server_base_url, data=body)
        assert resp.status_code == 405

    def test_post(self, requests_lite, server_base_url):
        body = testing.rand_string(_SIZE_1_KB // 2, _SIZE_1_KB)
        resp = requests_lite.post(server_base_url, data=body)
        assert resp.status_code == 200
        assert resp.text == body

    def test_post_invalid_content_length(self, requests_lite, server_base_url):
        headers = {'Content-Length': 'invalid'}
        resp = requests_lite.post(server_base_url, headers=headers)
        assert resp.status_code == 400

    def test_post_read_bounded_stream(self, requests_lite, server_base_url):
        body = testing.rand_string(_SIZE_1_KB // 2, _SIZE_1_KB)
        resp = requests_lite.post(server_base_url + 'bucket', data=body)
        assert resp.status_code == 200
        assert resp.text == body

    def test_post_read_bounded_stream_no_body(self, requests_lite, server_base_url):
        resp = requests_lite.post(server_base_url + 'bucket')
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

    print(f'wsgiref server is starting on {host}:{port}...')
    server = wsgiref.simple_server.make_server(host, port, application)

    while not stop_event.is_set():
        server.handle_request()

    print('wsgiref server is exiting (stop event set)...')


def _start_server(port, base_url, requests_lite):
    stop_event = multiprocessing.Event()
    process = multiprocessing.Process(
        target=_run_server,
        # NOTE(kgriffs): Pass these explicitly since if multiprocessing is
        #   using the 'spawn' start method, we can't depend on closures.
        args=(stop_event, _SERVER_HOST, port),
        daemon=True,
    )

    process.start()

    # NOTE(vytas): Give the server some time to start.
    start_time = time.time()
    while time.time() - start_time < _STARTUP_TIMEOUT:
        try:
            requests_lite.get(base_url, timeout=1.0)
        except OSError:
            time.sleep(0.2)
        else:
            break
    else:
        if process.is_alive():
            pytest.fail('server {base_url} is not responding to requests')
        else:
            return None

    return process, stop_event


@pytest.fixture(scope='module')
def server_base_url(requests_lite):
    for attempt in range(_START_ATTEMPTS):
        server_port = testing.get_unused_port()
        base_url = f'http://{_SERVER_HOST}:{server_port}/'
        if server_details := _start_server(server_port, base_url, requests_lite):
            break
    else:
        pytest.fail(f'could not start a wsgiref server in {_START_ATTEMPTS} attempts.')

    yield base_url

    process, stop_event = server_details
    stop_event.set()

    # NOTE(kgriffs): Pump the request handler loop in case execution
    # made it to the next server.handle_request() before we sent the
    # event.
    try:
        requests_lite.get(base_url, timeout=1.0)
    except OSError:
        pass  # Process already exited

    process.join()
