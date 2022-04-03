from http import HTTPStatus

import falcon


class Pong:
    async def on_get(self, req, resp):
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = 'PONG\n'
        resp.status = HTTPStatus.OK
