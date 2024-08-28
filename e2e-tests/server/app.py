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
    # TODO(vytas): Type to App's constructor.
    app = falcon.asgi.App()  # type: ignore

    hub = Hub()
    app.add_route('/ping', Pong())
    app.add_route('/sse', Events(hub))
    app.add_route('/ws/{name}', Chat(hub))

    app.add_static_route('/static', STATIC)

    return app
