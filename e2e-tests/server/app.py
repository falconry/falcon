import pathlib

import falcon
import falcon.asgi

from .chat import Chat
from .hub import Hub
from .ping import Pong

HERE = pathlib.Path(__file__).resolve().parent
STATIC = HERE.parent / 'static'


def create_app():
    app = falcon.asgi.App()

    hub = Hub()
    chat = Chat(hub)

    app.add_route('/ping', Pong())
    app.add_route('/sse', hub)
    app.add_route('/ws/{name}', chat)

    app.add_static_route('/static', str(STATIC))

    return app
