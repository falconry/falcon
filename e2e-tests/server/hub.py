import asyncio

import falcon.asgi


class Emitter:

    async def events(self):
        while True:
            await asyncio.sleep(2)

            yield falcon.asgi.SSEvent(text='Hello')

            await asyncio.sleep(5)

            yield falcon.asgi.SSEvent(text='A message')
            yield falcon.asgi.SSEvent(json={'msg': 'Hello!'})

            await asyncio.sleep(5)

            yield falcon.asgi.SSEvent(data=b'data', event_id='1337')

            await asyncio.sleep(15)


class Hub:

    def __init__(self):
        self._emitters = set()

    async def on_get(self, req, resp):
        emitter = Emitter()

        resp.sse = emitter.events()
