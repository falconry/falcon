from http import HTTPStatus

import falcon
import falcon.asgi


class Pong:

    async def on_get(self, req, resp):
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = 'PONG\n'
        resp.status = HTTPStatus.OK


def create_app():
    app = falcon.asgi.App()

    app.add_route('/ping', Pong())

    return app
