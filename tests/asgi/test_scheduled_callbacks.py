from collections import Counter
import time

import pytest

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
