import pathlib

import falcon
import falcon.asgi

from .chat import Chat
from .hub import Events
from .hub import Hub
from .ping import Pong

HERE = pathlib.Path(__file__).resolve().parent
STATIC = HERE.parent / 'static'


def create_app() -> falcon.asgi.App:
    app = falcon.asgi.App()

    # NOTE(vytas): E2E tests run Uvicorn, and the latest versions support ASGI
    #   HTTP/WSspec ver 2.4, so buffering on our side should not be needed.
    app.ws_options.max_receive_queue = 0

    hub = Hub()
    app.add_route('/ping', Pong())
    app.add_route('/sse', Events(hub))
    app.add_route('/ws/{name}', Chat(hub))

    app.add_static_route('/static', STATIC)

    return app
