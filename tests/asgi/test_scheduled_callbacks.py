import asyncio
from collections import Counter
import time

import pytest

from falcon import runs_sync
from falcon import testing
from falcon.asgi import App


def test_multiple():
    class SomeResource:
        def __init__(self):
            self.counter = Counter()

        async def on_get(self, req, resp):
            async def background_job_async():
                self.counter['backround:on_get:async'] += 1

            def background_job_sync():
                self.counter['backround:on_get:sync'] += 20

            with pytest.raises(TypeError):
                resp.schedule(background_job_sync)

            resp.schedule_sync(background_job_sync)
            resp.schedule(background_job_async)
            resp.schedule_sync(background_job_sync)
            resp.schedule(background_job_async)

        async def on_post(self, req, resp):
            async def background_job_async():
                self.counter['backround:on_get:async'] += 1000

            def background_job_sync():
                self.counter['backround:on_get:sync'] += 2000

            resp.schedule(background_job_async)
            resp.schedule(background_job_async)
            resp.schedule_sync(background_job_sync)
            resp.schedule_sync(background_job_sync)

        async def on_put(self, req, resp):
            async def background_job_async():
                self.counter['backround:on_get:async'] += 1000

            c = background_job_async()

            try:
                resp.schedule(c)
            finally:
                await c

    resource = SomeResource()

    app = App()
    app.add_route('/', resource)

    client = testing.TestClient(app)

    client.simulate_get()
    client.simulate_post()

    time.sleep(0.5)

    assert resource.counter['backround:on_get:async'] == 2002
    assert resource.counter['backround:on_get:sync'] == 4040

    result = client.simulate_put()
    assert result.status_code == 500

    # NOTE(kgriffs): Remove default handlers so that we can check the raised
    #   exception is what we expecte.
    app._error_handlers.clear()
    with pytest.raises(TypeError) as exinfo:
        client.simulate_put()

    assert 'coroutine' in str(exinfo.value)


class SimpleCallback:
    def __init__(self):
        self.called = 0
        self.event = asyncio.Event()

    async def _call_me(self):
        self.called += 1
        self.event.set()

    async def on_get(self, req, resp):
        resp.content_type = 'text/plain'
        resp.data = b'Hello, World!\n'
        resp.schedule(self._call_me)

    on_head = on_get

    async def on_get_sse(self, req, resp):
        async def nop_emitter():
            yield None

        resp.sse = nop_emitter()
        resp.schedule(self._call_me)

    async def on_get_stream(self, req, resp):
        async def stream():
            yield b'One\n'
            yield b'Two\n'
            yield b'Three\n'

        resp.content_type = 'text/plain'
        resp.stream = stream()
        resp.schedule(self._call_me)


@pytest.fixture()
def simple_resource():
    return SimpleCallback()


@pytest.fixture()
def callback_app(simple_resource):
    app = App()
    app.add_route('/', simple_resource)
    app.add_route('/sse', simple_resource, suffix='sse')
    app.add_route('/stream', simple_resource, suffix='stream')

    return app


@pytest.mark.parametrize('method,uri,expected', [
    ('GET', '/', 'Hello, World!\n'),
    ('HEAD', '/', ''),
    ('GET', '/sse', ': ping\n\n'),
    ('GET', '/stream', 'One\nTwo\nThree\n'),
])
@runs_sync
async def test_callback(callback_app, simple_resource, method, uri, expected):
    async with testing.ASGIConductor(callback_app) as conductor:
        resp = await conductor.simulate_request(method, uri)
        assert resp.status_code == 200
        assert resp.text == expected

        await asyncio.wait_for(simple_resource.event.wait(), 3.0)

        assert simple_resource.called == 1
