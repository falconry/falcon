import timeit

import falcon
from .wsgi import ENVIRON_BOILERPLATE


class Greeter:
    def on_get(self, req, resp):
        resp.content_type = 'text/plain; charset=utf-8'
        resp.text = 'Hello, World!'


def create_app():
    app = falcon.App()
    app.add_route('/', Greeter())
    return app


def run():
    def start_response(status, headers, exc_info=None):
        assert status == '200 OK'

    def request():
        return b''.join(app(environ, start_response))

    app = create_app()
    environ = ENVIRON_BOILERPLATE.copy()

    timeit.timeit(request, number=20000)


if __name__ == '__main__':
    run()
