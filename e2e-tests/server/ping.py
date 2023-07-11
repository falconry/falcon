from http import HTTPStatus

import falcon
from falcon.asgi import Request, Response


class Pong:
    async def on_get(self, req: Request, resp: Response) -> None:
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = 'PONG\n'
        resp.status = HTTPStatus.OK
