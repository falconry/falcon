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
                        self._queue.get(), timeout=self.POLL_TIMEOUT
                    )
                    yield event
                except asyncio.TimeoutError:
                    # NOTE(vytas): Keep the connection alive.
                    yield None
        finally:
            # TODO(vytas): Is there a more elegant way to detect a disconnect?
            self._done = True

    async def enqueue(self, message):
        event = SSEvent(text=message, event_id=str(uuid.uuid4()))
        await self._queue.put(event)

    @property
    def done(self):
        return self._done


class Hub:
    def __init__(self):
        self._emitters = set()
        self._users = {}

    def _update_emitters(self):
        done = {emitter for emitter in self._emitters if emitter.done}
        self._emitters.difference_update(done)
        return self._emitters.copy()

    def add_user(self, name, ws):
        self._users[name] = ws

    def remove_user(self, name):
        self._users.pop(name, None)

    async def broadcast(self, message):
        for emitter in self._update_emitters():
            await emitter.enqueue(message)

    async def message(self, name, text):
        ws = self._users.get(name)
        if ws:
            # TODO(vytas): What if this overlaps with another ongoing send?
            await ws.send_text(text)

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
