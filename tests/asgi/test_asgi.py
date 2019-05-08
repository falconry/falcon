import asyncio
from collections import Counter
from io import StringIO
import logging
import multiprocessing
import os
import time

import pytest
import requests
import uvicorn

import falcon
import falcon.asgi
import falcon.testing as testing

_SERVER_HOST = '127.0.0.1'
_SERVER_PORT = 9000 + os.getpid() % 100  # Facilitates parallel test execution
_SERVER_BASE_URL = 'http://{}:{}/'.format(_SERVER_HOST, _SERVER_PORT)
_SIZE_1_KB = 1024


@pytest.mark.usefixtures('_setup_asgi_server')
class TestASGIServer:

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

    def test_post_multiple(self):
        body = testing.rand_string(_SIZE_1_KB / 2, _SIZE_1_KB)
        resp = requests.post(_SERVER_BASE_URL, data=body)
        assert resp.status_code == 200
        assert resp.text == body
        assert resp.headers['X-Counter'] == '0'

        time.sleep(0.5)

        resp = requests.post(_SERVER_BASE_URL, data=body)
        assert resp.headers['X-Counter'] == '2002'

    def test_post_invalid_content_length(self):
        headers = {'Content-Length': 'invalid'}

        # NOTE(kgriffs): Uvicorn will kill the request so it does not
        #   even get to our app; the app logic is tested on the WSGI
        #   side. We leave this here in case something changes in
        #   the way uvicorn handles it or something and we want to
        #   get a heads-up if the request is no longer blocked.
        with pytest.raises(Exception):
            requests.post(_SERVER_BASE_URL, headers=headers)

    def test_post_read_bounded_stream(self):
        body = testing.rand_string(_SIZE_1_KB / 2, _SIZE_1_KB)
        resp = requests.post(_SERVER_BASE_URL + 'bucket', data=body)
        assert resp.status_code == 200
        assert resp.text == body

    def test_post_read_bounded_stream_no_body(self):
        resp = requests.post(_SERVER_BASE_URL + 'bucket')
        assert not resp.text

    def test_sse(self):
        resp = requests.get(_SERVER_BASE_URL + 'events')
        assert resp.status_code == 200

        events = resp.text.split('\n\n')
        assert len(events) > 2
        for e in events[:-1]:
            assert e == 'data: hello world'

        assert not events[-1]


def _run_server(succeeded):
    output = StringIO()
    logger = logging.getLogger('uvicorn')
    logger.addHandler(logging.StreamHandler(output))

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

    app = falcon.asgi.App()
    app.add_route('/', Things())
    app.add_route('/bucket', Bucket())
    app.add_route('/events', Events())

    lifespan_handler = LifespanHandler()
    app.add_lifespan_handler(lifespan_handler)

    uvicorn.run(app, host=_SERVER_HOST, port=_SERVER_PORT, loop='asyncio')

    assert lifespan_handler.startup_succeeded
    assert lifespan_handler.shutdown_succeeded

    print(output.getvalue())

    succeeded.value = 1


@pytest.fixture
def _setup_asgi_server():
    succeeded = multiprocessing.Value('B', 0)
    process = multiprocessing.Process(target=_run_server, args=(succeeded,), daemon=True)
    process.start()

    # NOTE(kgriffs): Let the server start up
    time.sleep(0.2)
    assert process.is_alive()

    yield

    # NOTE(kgriffs): Pump the request handler loop in case execution
    # made it to the next server.handle_request() before we sent the
    # event.
    try:
        requests.get(_SERVER_BASE_URL)
    except Exception:
        pass  # Process already exited

    process.terminate()
    process.join()

    assert succeeded.value == 1
