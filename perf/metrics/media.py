import io
import timeit

import falcon
from .wsgi import ENVIRON_BOILERPLATE


class Items:
    def on_post(self, req, resp):
        item = req.get_media()
        item['id'] = itemid = 'bar001337'

        resp.location = f'{req.path}/{itemid}'
        resp.media = item
        resp.status = falcon.HTTP_CREATED


def create_app():
    app = falcon.App()
    app.add_route('/items', Items())
    return app


def run():
    def start_response(status, headers, exc_info=None):
        assert status == '201 Created'

    def request():
        environ['wsgi.input'].seek(0)

        assert b''.join(app(environ, start_response)) == (
            b'{"foo": "bar", "id": "bar001337"}')

    app = create_app()
    environ = ENVIRON_BOILERPLATE.copy()
    environ['CONTENT_LENGTH'] = len(b'{"foo": "bar"}')
    environ['CONTENT_TYPE'] = 'application/json'
    environ['PATH_INFO'] = '/items'
    environ['REQUEST_METHOD'] = 'POST'
    environ['wsgi.input'] = io.BytesIO(b'{"foo": "bar"}')

    timeit.timeit(request, number=20000)


if __name__ == '__main__':
    run()
