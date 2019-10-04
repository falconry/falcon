import asyncio
from collections import Counter
from io import StringIO
import logging
import multiprocessing
import random
import time

import pytest
import requests
import requests.exceptions
import uvicorn

import falcon
import falcon.asgi
import falcon.testing as testing
import falcon.util

_SERVER_HOST = '127.0.0.1'
_SIZE_1_KB = 1024

_random = random.Random()


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

        # NOTE(kgriffs): Uvicorn will kill the request so it does not
        #   even get to our app; the app logic is tested on the WSGI
        #   side. We leave this here in case something changes in
        #   the way uvicorn handles it or something and we want to
        #   get a heads-up if the request is no longer blocked.
        with pytest.raises(Exception):
            requests.post(server_base_url, headers=headers)

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
            await asyncio.sleep(0.1)
            self._counter['backround:things:on_post'] += 1

        def background_job_sync():
            time.sleep(0.1)
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
            time.sleep(0.001)
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


def _run_server(succeeded, host, port):
    output = StringIO()
    logger = logging.getLogger('uvicorn')
    logger.addHandler(logging.StreamHandler(output))

    app = falcon.asgi.App()
    app.add_route('/', Things())
    app.add_route('/bucket', Bucket())
    app.add_route('/events', Events())

    lifespan_handler = LifespanHandler()
    app.add_lifespan_handler(lifespan_handler)

    try:
        uvicorn.run(app, host=host, port=port, loop='asyncio')
    except Exception as ex:
        print(ex, type(ex))
    except SystemExit:
        pass
        # e = sys.exc_info()[0]
        # print(e, type(e))

    assert lifespan_handler.startup_succeeded
    assert lifespan_handler.shutdown_succeeded

    print(output.getvalue())

    succeeded.value = 1


@pytest.fixture
def server_base_url():
    # NOTE(kgriffs): This facilitates parallel test execution as well as
    #   mitigating the problem of trying to reuse a port that the system
    #   hasn't cleaned up yet.
    # NOTE(kgriffs): Use our own Random instance because we don't want
    #   pytest messing with the seed.
    server_port = _random.randint(50000, 60000)
    base_url = 'http://{}:{}/'.format(_SERVER_HOST, server_port)

    # NOTE(kgriffs): We have to use spawn instead of the default fork method,
    #   since forking has a bad interaction (root cause TBD) with Cython and
    #   concurrent.futures.ThreadPoolExecutor that results in scheduled
    #   tasks never completing in asgi/test_sync.py
    ctx = multiprocessing.get_context('spawn')

    succeeded = ctx.Value('B', 0)
    process = ctx.Process(
        target=_run_server,
        daemon=True,

        # NOTE(kgriffs): Pass these explicitly since if multiprocessing is
        #   using the 'spawn' start method, we can't depend on closures.
        args=(succeeded, _SERVER_HOST, server_port),
    )
    process.start()

    # NOTE(kgriffs): Let the server start up.
    while True:
        try:
            requests.get(base_url, timeout=0.2)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            time.sleep(0.2)
        else:
            break

    assert process.is_alive()

    yield base_url

    # NOTE(kgriffs): Pump the request handler loop in case execution
    # made it to the next server.handle_request() before we sent the
    # event.
    try:
        requests.get(base_url)
    except Exception:
        pass  # Process already exited

    process.terminate()
    process.join()

    assert succeeded.value == 1
