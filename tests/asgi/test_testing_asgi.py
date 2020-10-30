import time

import pytest

from falcon import testing


@pytest.mark.asyncio
async def test_asgi_request_event_emitter_hang():
    # NOTE(kgriffs): This tests the ASGI server behavior that
    #   ASGIRequestEventEmitter simulates when emit() is called
    #   again after there are no more events available.

    expected_elapsed_min = 1
    disconnect_at = time.time() + expected_elapsed_min

    emit = testing.ASGIRequestEventEmitter(disconnect_at=disconnect_at)

    start = time.time()
    while True:
        event = await emit()
        if not event.get('more_body', False):
            break

    elapsed = time.time() - start
    assert elapsed < 0.1

    start = time.time()
    await emit()
    elapsed = time.time() - start

    assert (elapsed + 0.1) > expected_elapsed_min


@pytest.mark.asyncio
async def test_ignore_extra_asgi_events():
    collect = testing.ASGIResponseEventCollector()

    await collect({'type': 'http.response.start', 'status': 200})
    await collect({'type': 'http.response.body', 'more_body': False})

    # NOTE(kgriffs): Events after more_body is False are ignored to conform
    #   to the ASGI spec.
    await collect({'type': 'http.response.body'})
    assert len(collect.events) == 2


@pytest.mark.asyncio
async def test_invalid_asgi_events():
    collect = testing.ASGIResponseEventCollector()

    def make_event(headers=None, status=200):
        return {
            'type': 'http.response.start',
            'headers': headers or [],
            'status': status
        }

    with pytest.raises(TypeError):
        await collect({'type': 123})

    with pytest.raises(TypeError):
        headers = [
            ('notbytes', b'bytes')
        ]
        await collect(make_event(headers))

    with pytest.raises(TypeError):
        headers = [
            (b'bytes', 'notbytes')
        ]
        await collect(make_event(headers))

    with pytest.raises(ValueError):
        headers = [
            # NOTE(kgriffs): Name must be lowercase
            (b'Content-Type', b'application/json')
        ]
        await collect(make_event(headers))

    with pytest.raises(TypeError):
        await collect(make_event(status='200'))

    with pytest.raises(TypeError):
        await collect(make_event(status=200.1))

    with pytest.raises(TypeError):
        await collect({'type': 'http.response.body', 'body': 'notbytes'})

    with pytest.raises(TypeError):
        await collect({'type': 'http.response.body', 'more_body': ''})

    with pytest.raises(ValueError):
        # NOTE(kgriffs): Invalid type
        await collect({'type': 'http.response.bod'})


def test_is_asgi_app_cls():
    class Foo:
        @classmethod
        def class_meth(cls, scope, receive, send):
            pass

    assert testing.client._is_asgi_app(Foo.class_meth)
