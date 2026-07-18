import falcon
import falcon.asgi


async def handle_overflow(req, resp, ex, params):
    if params.get('power', 0) >= 1000:
        raise falcon.HTTPBadRequest(title='Too Damn High!')

    resp.content_type = falcon.MEDIA_TEXT
    resp.text = 'That was too much to handle... Check your parameters.\n'
    resp.status = falcon.HTTP_422


class Exponentiation:
    async def on_get(self, req, resp, base, power):
        resp.media = base**power


app = falcon.asgi.App()
app.add_error_handler(OverflowError, handle_overflow)
app.add_route('/exponentiation/{base:float}/{power:float}', Exponentiation())
