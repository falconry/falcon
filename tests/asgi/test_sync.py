import asyncio
import time

import pytest

from falcon import testing
from falcon.asgi import App
import falcon.util


def test_sync_helpers():
    safely_values = []
    unsafely_values = []
    shirley_values = []

    class SomeResource:
        async def on_get(self, req, resp):
            safely_coroutine_objects = []
            unsafely_coroutine_objects = []
            shirley_coroutine_objects = []

            def callme_safely(a, b, c=None):
                # NOTE(kgriffs): Sleep to prove that there isn't another
                #   instance running in parallel that is able to race ahead.
                time.sleep(0.001)
                safely_values.append((a, b, c))

            def callme_unsafely(a, b, c=None):
                time.sleep(0.01)

                # NOTE(vytas): Deliberately exaggerate a race condition here
                #   in order to ensure a more deterministic test outcome.
                if a == 137:
                    for _ in range(1000):
                        if len(unsafely_values) > 137:
                            break
                        time.sleep(0.01)

                unsafely_values.append((a, b, c))

            def callme_shirley(a=42, b=None):
                time.sleep(0.01)
                v = (a, b)
                shirley_values.append(v)

                # NOTE(kgriffs): Test that returning values works as expected
                return v

            # NOTE(kgriffs): Test setting threadsafe=True explicitly
            cmus = falcon.util.wrap_sync_to_async(callme_unsafely, threadsafe=True)
            cms = falcon.util.wrap_sync_to_async(callme_safely, threadsafe=False)

            loop = falcon.util.get_running_loop()

            # NOTE(kgriffs): create_task() is used here, so that the coroutines
            #   are scheduled immediately in the order created; under Python
            #   3.6, asyncio.gather() does not seem to always schedule
            #   them in order, so we do it this way to make it predictable.
            for i in range(1000):
                safely_coroutine_objects.append(
                    loop.create_task(cms(i, i + 1, c=i + 2))
                )
                unsafely_coroutine_objects.append(
                    loop.create_task(cmus(i, i + 1, c=i + 2))
                )
                shirley_coroutine_objects.append(
                    loop.create_task(falcon.util.sync_to_async(callme_shirley, 24, b=i))
                )

            await asyncio.gather(
                *(
                    safely_coroutine_objects +
                    unsafely_coroutine_objects +
                    shirley_coroutine_objects
                )
            )

            assert (42, None) == await falcon.util.sync_to_async(callme_shirley)
            assert (1, 2) == await falcon.util.sync_to_async(callme_shirley, 1, 2)
            assert (3, 4) == await falcon.util.sync_to_async(callme_shirley, 3, b=4)

            assert (5, None) == await falcon.util.wrap_sync_to_async(callme_shirley)(5)
            assert (42, 6) == await falcon.util.wrap_sync_to_async(
                callme_shirley, threadsafe=True)(b=6)

            with pytest.raises(TypeError):
                await falcon.util.sync_to_async(callme_shirley, -1, bogus=-1)

    resource = SomeResource()

    app = App()
    app.add_route('/', resource)

    client = testing.TestClient(app)

    result = client.simulate_get()
    assert result.status_code == 200

    assert len(safely_values) == 1000
    for i, val in enumerate(safely_values):
        assert val == (i, i + 1, i + 2)

    assert len(unsafely_values) == 1000
    assert any(
        val != (i, i + 1, i + 2)
        for i, val in enumerate(unsafely_values)
    )

    for i, val in enumerate(shirley_values):
        assert val[0] in {24, 42, 1, 5, 3}
        assert val[1] is None or (0 <= val[1] < 1000)
