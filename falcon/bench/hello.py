import sys
from timeit import repeat

import flask
import werkzeug.wrappers as werkzeug

sys.path.append('../..')
import falcon
import falcon.test.helpers as helpers


def create_falcon(body, headers):
    falcon_app = falcon.API()

    class HelloResource:
        def on_get(self, req, resp):
            resp.body = body
            resp.set_header('Content-Type', 'text/plain')
            resp.set_headers(headers)

    falcon_app.add_route('/', HelloResource())

    return falcon_app


def create_flask(body, headers):
    flask_app = flask.Flask('hello')

    @flask_app.route('/')
    def hello():
        return flask.Response(headers=headers, data=body)

    return flask_app


def create_werkzeug(body, headers):
    @werkzeug.Request.application
    def hello(request):
        return werkzeug.Response(body, headers=headers)

    return hello


def avg(array):
    return sum(array) / len(array)


def bench(name):
    iterations = 1000000

    func = create_bench(name)
    results = repeat(func, number=iterations)

    print('{0}: {1:0.6f} ms/req'.format(name, avg(results) / iterations))


def create_bench(name):
    srmock = helpers.StartResponseMock()
    env = helpers.create_environ()
    body = helpers.rand_string(10240, 10240)
    headers = {'X-Test': 'Funky Chicken'}

    if name == 'Flask':
        app = create_flask(body, headers)
    elif name == 'Werkzeug':
        app = create_werkzeug(body, headers)
    else:
        app = create_falcon(body, headers)

    def bench():
        app(env, srmock)

    return bench


if __name__ == '__main__':
    bench('Flask')
    bench('Werkzeug')
    bench('Falcon')
