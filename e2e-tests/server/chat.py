import re

from falcon.asgi import Request
from falcon.asgi import WebSocket

from .hub import Hub


class Chat:
    ALL = re.compile(r'^/all\s+(.+)$')
    MSG = re.compile(r'^/msg\s+(\w+)\s+(.+)$')

    def __init__(self, hub: Hub):
        self._hub = hub

    async def on_websocket(self, req: Request, ws: WebSocket, name: str) -> None:
        await ws.accept()

        try:
            await self._hub.broadcast(f'{name} CONNECTED')
            self._hub.add_user(name, ws)

            await ws.send_text(f'Hello, {name}!')

            while True:
                message = await ws.receive_text()

                if message == '/quit':
                    await ws.send_text(f'Bye, {name}!')
                    await ws.close(4001, 'quit command')
                    break

                command = self.ALL.match(message)
                if command:
                    text = command.group(1)
                    await self._hub.broadcast(f'[{name}] {text}')
                    continue

                command = self.MSG.match(message)
                if command:
                    recipient, text = command.groups()
                    await self._hub.message(recipient, f'[{name}] {text}')
                    continue

                await ws.send_text('Supported commands: /all /msg /quit')

        finally:
            self._hub.remove_user(name)
            await self._hub.broadcast(f'{name} DISCONNECTED')
