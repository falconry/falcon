import io

import falcon
from .wsgi import run


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


if __name__ == '__main__':
    run(
        create_app(),
        {
            'CONTENT_LENGTH': len(b'{"foo": "bar"}'),
            'CONTENT_TYPE': 'application/json',
            'PATH_INFO': '/items',
            'REQUEST_METHOD': 'POST',
            'wsgi.input': io.BytesIO(b'{"foo": "bar"}'),
        },
        '201 Created',
        b'{"foo": "bar", "id": "bar001337"}',
    )
