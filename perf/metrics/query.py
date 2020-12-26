import falcon
from .wsgi import run


class QueryParams:
    def on_get(self, req, resp):
        resp.set_header('X-Falcon', req.get_header('X-Falcon'))
        resp.status = req.get_param_as_int('resp_status')
        resp.text = req.get_param('framework')


def create_app():
    app = falcon.App()
    app.add_route('/path', QueryParams())
    return app


if __name__ == '__main__':
    run(
        create_app(),
        {
            'HTTP_X_FRAMEWORK': 'falcon',
            'HTTP_X_FALCON': 'peregrine',
            'PATH_INFO': '/path',
            'QUERY_STRING': (
                'flag1&flag2=&flag3&framework=falcon&resp_status=204&'
                'fruit=apple&flag4=true&fruit=orange&status=%F0%9F%8E%89&'
                'fruit=banana'
            ),
        },
        '204 No Content',
        b'',
    )
