import asyncio
import uuid

from falcon.asgi import SSEvent


class Emitter:
    POLL_TIMEOUT = 3.0

    def __init__(self):
        self._done = False
        self._queue = asyncio.Queue()

    async def events(self):
        try:
            yield SSEvent(text='SSE CONNECTED')
            while True:
                try:
                    event = await asyncio.wait_for(
                        self._queue.get(), timeout=self.POLL_TIMEOUT)
                    yield event
                except asyncio.TimeoutError:
                    # NOTE(vytas): Keep the connection alive.
                    yield None
        finally:
            # TODO(vytas): Is there a more elegant way to detect a disconnect?
            self._done = True

    def enqueue(self, message, topic=None):
        event = SSEvent(text=message, event=topic, event_id=uuid.uuid4())
        self._queue.put_nowait(event)

    @property
    def done(self):
        return self._done


class Hub:
    def __init__(self):
        self._emitters = set()

    def _update_emitters(self):
        done = {emitter for emitter in self._emitters if emitter.done}
        self._emitters.difference_update(done)
        return self._emitters.copy()

    def broadcast(self, message, topic=None):
        for emitter in self._update_emitters():
            emitter.enqueue(message, topic=topic)

    def events(self):
        emitter = Emitter()
        self._update_emitters()
        self._emitters.add(emitter)
        return emitter.events()


class Events:
    def __init__(self, hub):
        self._hub = hub

    async def on_get(self, req, resp):
        resp.sse = self._hub.events()
