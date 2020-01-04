from contextlib import contextmanager
import os
import platform
import random
import subprocess
import time

import pytest
import requests
import requests.exceptions

from falcon import testing


_MODULE_DIR = os.path.abspath(os.path.dirname(__file__))

_PYPY = platform.python_implementation() == 'PyPy'

_SERVER_HOST = '127.0.0.1'
_SIZE_1_KB = 1024

_random = random.Random()


_REQUEST_TIMEOUT = 10


class TestASGIServer:

    def test_get(self, server_base_url):
        resp = requests.get(server_base_url, timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200
        assert resp.text == '127.0.0.1'

    def test_put(self, server_base_url):
        body = '{}'
        resp = requests.put(server_base_url, data=body, timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200
        assert resp.text == '{}'

    def test_head_405(self, server_base_url):
        body = '{}'
        resp = requests.head(server_base_url, data=body, timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 405

    def test_post_multiple(self, server_base_url):
        body = testing.rand_string(_SIZE_1_KB / 2, _SIZE_1_KB)
        resp = requests.post(server_base_url, data=body, timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200
        assert resp.text == body
        assert resp.headers['X-Counter'] == '0'

        time.sleep(1)

        resp = requests.post(server_base_url, data=body, timeout=_REQUEST_TIMEOUT)
        assert resp.headers['X-Counter'] == '2002'

    def test_post_invalid_content_length(self, server_base_url):
        headers = {'Content-Length': 'invalid'}

        try:
            resp = requests.post(server_base_url, headers=headers, timeout=_REQUEST_TIMEOUT)

            # Daphne responds with a 400
            assert resp.status_code == 400

        except requests.ConnectionError:
            # NOTE(kgriffs): Uvicorn will kill the request so it does not
            #   even get to our app; the app logic is tested on the WSGI
            #   side. We leave this here in case something changes in
            #   the way uvicorn handles it or something and we want to
            #   get a heads-up if the request is no longer blocked.
            pass

    def test_post_read_bounded_stream(self, server_base_url):
        body = testing.rand_string(_SIZE_1_KB / 2, _SIZE_1_KB)
        resp = requests.post(server_base_url + 'bucket', data=body, timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200
        assert resp.text == body

    def test_post_read_bounded_stream_no_body(self, server_base_url):
        resp = requests.post(server_base_url + 'bucket', timeout=_REQUEST_TIMEOUT)
        assert not resp.text

    def test_sse(self, server_base_url):
        resp = requests.get(server_base_url + 'events', timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200

        events = resp.text.split('\n\n')
        assert len(events) > 2
        for e in events[:-1]:
            assert e == 'data: hello world'

        assert not events[-1]


@contextmanager
def _run_server_isolated(process_factory, host, port):
    # NOTE(kgriffs): We have to use subprocess because uvicorn has a tendency
    #   to corrupt our asyncio state and cause intermittent hangs in the test
    #   suite.
    print('\n[Starting server process...]')
    server = process_factory(host, port)

    time.sleep(0.2)
    startup_succeeded = (server.poll() is None)
    print('\n[Server process start {}]'.format('succeeded' if startup_succeeded else 'failed'))

    if startup_succeeded:
        yield server

    print('\n[Sending SIGTERM to server process...]')
    server.terminate()

    try:
        server.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()
        server.communicate()

    assert server.returncode == 0
    assert startup_succeeded


def _uvicorn_factory(host, port):
    # NOTE(vytas): uvicorn+uvloop is not (well) supported on PyPy at the time
    #   of writing.
    loop_options = ('--http', 'h11', '--loop', 'asyncio') if _PYPY else ()
    options = (
        '--host', host,
        '--port', str(port),

        '_asgi_test_app:application'
    )

    return subprocess.Popen(
        ('uvicorn',) + loop_options + options,
        cwd=_MODULE_DIR,
    )


def _daphne_factory(host, port):
    return subprocess.Popen(
        (
            'daphne',

            '--bind', host,
            '--port', str(port),

            '--verbosity', '2',
            '--access-log', '-',

            '_asgi_test_app:application'
        ),
        cwd=_MODULE_DIR,
    )


@pytest.fixture(params=[_uvicorn_factory, _daphne_factory])
def server_base_url(request):
    process_factory = request.param

    # NOTE(kgriffs): This facilitates parallel test execution as well as
    #   mitigating the problem of trying to reuse a port that the system
    #   hasn't cleaned up yet.
    # NOTE(kgriffs): Use our own Random instance because we don't want
    #   pytest messing with the seed.
    server_port = _random.randint(50000, 60000)
    base_url = 'http://{}:{}/'.format(_SERVER_HOST, server_port)

    with _run_server_isolated(process_factory, _SERVER_HOST, server_port):
        # NOTE(kgriffs): Let the server start up. Give up after 5 seconds.
        start_ts = time.time()
        while True:
            wait_time = time.time() - start_ts
            assert wait_time < 5

            try:
                requests.get(base_url, timeout=0.2)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                time.sleep(0.2)
            else:
                break

        yield base_url
