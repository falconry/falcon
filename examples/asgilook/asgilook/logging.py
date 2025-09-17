import logging

import falcon

logging.basicConfig(level=logging.INFO)


class ErrorResource:
    def on_get(self, req, resp):
        raise Exception('Something went wrong!')


app = falcon.App()
app.add_route('/error', ErrorResource())