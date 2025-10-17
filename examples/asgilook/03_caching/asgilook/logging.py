import logging

import falcon.asgi

logging.basicConfig(level=logging.INFO)


class ErrorResource:
    async def on_get(self, req, resp):
        raise Exception('Something went wrong!')


app = falcon.asgi.App()
app.add_route('/error', ErrorResource())