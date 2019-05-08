from collections import Counter
import time

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

            resp.schedule(background_job_async)
            resp.schedule(background_job_sync)
            resp.schedule(background_job_async)
            resp.schedule(background_job_sync)

        async def on_post(self, req, resp):
            async def background_job_async():
                self.counter['backround:on_get:async'] += 1000

            def background_job_sync():
                self.counter['backround:on_get:sync'] += 2000

            resp.schedule(background_job_async)
            resp.schedule(background_job_async)
            resp.schedule(background_job_sync)
            resp.schedule(background_job_sync)

    resource = SomeResource()

    app = App()
    app.add_route('/', resource)

    client = testing.TestClient(app)

    client.simulate_get()
    client.simulate_post()

    time.sleep(0.5)

    assert resource.counter['backround:on_get:async'] == 2002
    assert resource.counter['backround:on_get:sync'] == 4040
