import timeit

import falcon.asgi
from .common import get_work_factor

SCOPE_BOILERPLATE = {
    'asgi': {'version': '3.0', 'spec_version': '2.1'},
    'headers': [[b'host', b'falconframework.org']],
    'http_version': '1.1',
    'method': 'GET',
    'path': '/',
    'query_string': b'',
    'server': ['falconframework.org', 80],
    'type': 'http',
}

RECEIVE_EVENT = {
    'type': 'http.request',
    'body': b'',
    'more_body': False,
}


class AsyncGreeter:
    async def on_get(self, req, resp):
        resp.content_type = 'text/plain; charset=utf-8'
        resp.text = 'Hello, World!\n'


def create_app():
    app = falcon.asgi.App()
    app.add_route('/', AsyncGreeter())
    return app


def run(app, expected_status, expected_body, number=None):
    async def receive():
        return receive_event

    async def send(event):
        if event['type'] == 'http.response.start':
            assert event['status'] == expected_status
        else:
            event['body'] == expected_body

    def request():
        try:
            app(scope, receive, send).send(None)
        except StopIteration:
            pass

    scope = SCOPE_BOILERPLATE.copy()
    receive_event = RECEIVE_EVENT.copy()

    if number is None:
        number = get_work_factor()

    timeit.timeit(request, number=number)


if __name__ == '__main__':
    run(create_app(), 200, b'Hello, World!')
