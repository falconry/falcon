import asyncio
from collections import Counter
from contextlib import contextmanager
import os
import platform
import random
import subprocess
import time

import pytest
import requests
import requests.exceptions

import falcon
from falcon import testing
import falcon.asgi
import falcon.util


_PYPY = platform.python_implementation() == 'PyPy'

_SERVER_HOST = '127.0.0.1'
_SIZE_1_KB = 1024

_random = random.Random()

_MODULE_DIR = os.path.abspath(os.path.dirname(__file__))
_MODULE_NAME, __ = os.path.splitext(os.path.basename(__file__))


class TestASGIServer:

    def test_get(self, server_base_url):
        resp = requests.get(server_base_url)
        assert resp.status_code == 200
        assert resp.text == '127.0.0.1'

    def test_put(self, server_base_url):
        body = '{}'
        resp = requests.put(server_base_url, data=body)
        assert resp.status_code == 200
        assert resp.text == '{}'

    def test_head_405(self, server_base_url):
        body = '{}'
        resp = requests.head(server_base_url, data=body)
        assert resp.status_code == 405

    def test_post_multiple(self, server_base_url):
        body = testing.rand_string(_SIZE_1_KB / 2, _SIZE_1_KB)
        resp = requests.post(server_base_url, data=body)
        assert resp.status_code == 200
        assert resp.text == body
        assert resp.headers['X-Counter'] == '0'

        time.sleep(1)

        resp = requests.post(server_base_url, data=body)
        assert resp.headers['X-Counter'] == '2002'

    def test_post_invalid_content_length(self, server_base_url):
        headers = {'Content-Length': 'invalid'}

        try:
            resp = requests.post(server_base_url, headers=headers)

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
        resp = requests.post(server_base_url + 'bucket', data=body)
        assert resp.status_code == 200
        assert resp.text == body

    def test_post_read_bounded_stream_no_body(self, server_base_url):
        resp = requests.post(server_base_url + 'bucket')
        assert not resp.text

    def test_sse(self, server_base_url):
        resp = requests.get(server_base_url + 'events')
        assert resp.status_code == 200

        events = resp.text.split('\n\n')
        assert len(events) > 2
        for e in events[:-1]:
            assert e == 'data: hello world'

        assert not events[-1]


class Things:
    def __init__(self):
        self._counter = Counter()

    async def on_get(self, req, resp):
        await asyncio.sleep(0.01)
        resp.body = req.remote_addr

    async def on_post(self, req, resp):
        resp.data = await req.stream.read(req.content_length or 0)
        resp.set_header('X-Counter', str(self._counter['backround:things:on_post']))

        async def background_job_async():
            await asyncio.sleep(0.01)
            self._counter['backround:things:on_post'] += 1

        def background_job_sync():
            time.sleep(0.01)
            self._counter['backround:things:on_post'] += 1000

        resp.schedule(background_job_async)
        resp.schedule(background_job_sync)
        resp.schedule(background_job_async)
        resp.schedule(background_job_sync)

    async def on_put(self, req, resp):
        # NOTE(kgriffs): Test that reading past the end does
        # not hang.

        chunks = []
        for i in range(req.content_length + 1):
            # NOTE(kgriffs): In the ASGI interface, bounded_stream is an
            #   alias for req.stream. We'll use the alias here just as
            #   a sanity check.
            chunk = await req.bounded_stream.read(1)
            chunks.append(chunk)

        # NOTE(kgriffs): body should really be set to a string, but
        #   Falcon is lenient and will allow bytes as well (although
        #   it is slightly less performant).
        # TODO(kgriffs): Perhaps in Falcon 4.0 be more strict? We would
        #   also have to change the WSGI behavior to match.
        resp.body = b''.join(chunks)

        # =================================================================
        # NOTE(kgriffs): Test the sync_to_async helpers here to make sure
        #   they work as expected in the context of a real ASGI server.
        # =================================================================
        safely_coroutine_objects = []
        safely_values = []

        def callmesafely(a, b, c=None):
            # NOTE(kgriffs): Sleep to prove that there isn't another instance
            #   running in parallel that is able to race ahead.
            time.sleep(0.0001)
            safely_values.append((a, b, c))

        cms = falcon.util.wrap_sync_to_async(callmesafely, threadsafe=False)
        loop = falcon.util.get_loop()
        for i in range(1000):
            # NOTE(kgriffs): create_task() is used here, so that the coroutines
            #   are scheduled immediately in the order created; under Python
            #   3.6, asyncio.gather() does not seem to always schedule
            #   them in order, so we do it this way to make it predictable.
            safely_coroutine_objects.append(loop.create_task(cms(i, i + 1, c=i + 2)))

        await asyncio.gather(*safely_coroutine_objects)

        assert len(safely_values) == 1000
        for i, val in enumerate(safely_values):
            assert safely_values[i] == (i, i + 1, i + 2)

        def callmeshirley(a=42, b=None):
            return (a, b)

        assert (42, None) == await falcon.util.sync_to_async(callmeshirley)
        assert (1, 2) == await falcon.util.sync_to_async(callmeshirley, 1, 2)
        assert (5, None) == await falcon.util.sync_to_async(callmeshirley, 5)
        assert (3, 4) == await falcon.util.sync_to_async(callmeshirley, 3, b=4)


class Bucket:
    async def on_post(self, req, resp):
        resp.body = await req.stream.read()


class Events:
    async def on_get(self, req, resp):
        async def emit():
            start = time.time()
            while time.time() - start < 1:
                yield falcon.asgi.SSEvent(text='hello world')
                await asyncio.sleep(0.2)

        resp.sse = emit()


class LifespanHandler:
    def __init__(self):
        self.startup_succeeded = False
        self.shutdown_succeeded = False

    async def process_startup(self, scope, event):
        assert scope['type'] == 'lifespan'
        assert event['type'] == 'lifespan.startup'
        self.startup_succeeded = True

    async def process_shutdown(self, scope, event):
        assert scope['type'] == 'lifespan'
        assert event['type'] == 'lifespan.shutdown'
        self.shutdown_succeeded = True


@contextmanager
def _run_server_isolated(process_factory, host, port):
    # NOTE(kgriffs): We have to use subprocess because uvicorn has a tendency
    #   to corrupt our asyncio state and cause intermittent hangs in the test
    #   suite.
    server = process_factory(host, port)

    time.sleep(0.2)
    server.poll()
    startup_succeeded = (server.returncode is None)

    if startup_succeeded:
        yield server

    server.terminate()

    try:
        stdout_data, __ = server.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()
        stdout_data, __ = server.communicate()

    print(stdout_data.decode())

    assert server.returncode == 0
    assert startup_succeeded


def _uvicorn_factory(host, port):
    # NOTE(vytas): uvicorn+uvloop is not (well) supported on PyPy at the time
    #   of writing.
    loop_options = ('--http', 'h11', '--loop', 'asyncio') if _PYPY else ()
    options = (
        '--host', host,
        '--port', str(port),

        _MODULE_NAME + ':application'
    )

    return subprocess.Popen(
        ('uvicorn',) + loop_options + options,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
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

            _MODULE_NAME + ':application'
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
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


def create_app():
    app = falcon.asgi.App()
    app.add_route('/', Things())
    app.add_route('/bucket', Bucket())
    app.add_route('/events', Events())

    lifespan_handler = LifespanHandler()
    app.add_lifespan_handler(lifespan_handler)

    return app


application = create_app()
