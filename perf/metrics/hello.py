import falcon
from .wsgi import run


class Greeter:
    def on_get(self, req, resp):
        resp.content_type = 'text/plain; charset=utf-8'
        resp.text = 'Hello, World!\n'


def create_app():
    app = falcon.App()
    app.add_route('/', Greeter())
    return app


if __name__ == '__main__':
    run(
        create_app(),
        {},
        '200 OK',
        b'Hello, World!\n',
    )
