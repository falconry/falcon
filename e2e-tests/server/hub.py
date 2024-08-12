from __future__ import annotations

import asyncio
import typing
import uuid

from falcon.asgi import Request
from falcon.asgi import Response
from falcon.asgi import SSEvent
from falcon.asgi import WebSocket


class Emitter:
    POLL_TIMEOUT = 3.0

    def __init__(self) -> None:
        self._done: bool = False
        self._queue: asyncio.Queue[SSEvent] = asyncio.Queue()

    async def events(self) -> typing.AsyncGenerator[typing.Optional[SSEvent], None]:
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

    async def enqueue(self, message: str) -> None:
        event = SSEvent(text=message, event_id=str(uuid.uuid4()))
        await self._queue.put(event)

    @property
    def done(self) -> bool:
        return self._done


class Hub:
    def __init__(self) -> None:
        self._emitters: set[Emitter] = set()
        self._users: dict[str, WebSocket] = {}

    def _update_emitters(self) -> set[Emitter]:
        done = {emitter for emitter in self._emitters if emitter.done}
        self._emitters.difference_update(done)
        return self._emitters.copy()

    def add_user(self, name: str, ws: WebSocket) -> None:
        self._users[name] = ws

    def remove_user(self, name: str) -> None:
        self._users.pop(name, None)

    async def broadcast(self, message: str) -> None:
        for emitter in self._update_emitters():
            await emitter.enqueue(message)

    async def message(self, name: str, text: str) -> None:
        ws = self._users.get(name)
        if ws:
            # TODO(vytas): What if this overlaps with another ongoing send?
            await ws.send_text(text)

    def events(self) -> typing.AsyncGenerator[typing.Optional[SSEvent], None]:
        emitter = Emitter()
        self._update_emitters()
        self._emitters.add(emitter)
        return emitter.events()


class Events:
    def __init__(self, hub: Hub):
        self._hub = hub

    async def on_get(self, req: Request, resp: Response) -> None:
        resp.sse = self._hub.events()
