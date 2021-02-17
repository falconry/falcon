class Chat:
    BANNED_USERS = frozenset({'banned', 'banned2'})

    def __init__(self, hub):
        self._hub = hub

    async def on_websocket(self, req, ws, name):
        if name in self.BANNED_USERS:
            return

        await ws.accept()

        await ws.send_text(f'Hello, {name}!')

        while True:
            message = await ws.receive_text()
            if message == '/quit':
                await ws.send_text('BYE')
                break

            await ws.send_text(message.upper())

        self._hub.broadcast(f'{name} DISCONNECTED')
