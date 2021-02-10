from http import HTTPStatus
import pathlib

import falcon
import falcon.asgi

HERE = pathlib.Path(__file__).resolve().parent
STATIC = HERE.parent / 'static'


class Pong:

    async def on_get(self, req, resp):
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = 'PONG\n'
        resp.status = HTTPStatus.OK


class Chat:

    async def on_websocket(self, req, ws, name):
        await ws.accept()

        await ws.send_text(f'Hello, {name}!')

        while True:
            message = await ws.receive_text()
            if message == '/quit':
                await ws.send_text('BYE')
                break

            await ws.send_text(message.upper())


def create_app():
    app = falcon.asgi.App()

    app.add_route('/ping', Pong())
    app.add_route('/ws/{name}', Chat())

    app.add_static_route('/static', str(STATIC))

    return app
