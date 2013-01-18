import sys
from timeit import repeat

import wheezy.http as wheezy
import bottle

import flask
import werkzeug.wrappers as werkzeug
from werkzeug.routing import Map, Rule

sys.path.append('./nuts/nuts')
import app as nuts
del sys.path[-1]

sys.path.append('../..')
import falcon
import falcon.test.helpers as helpers
del sys.path[-1]


def create_falcon(body, headers, path):
    falcon_app = falcon.API()

    class HelloResource:
        def on_get(self, req, resp):
            resp.body = body
            resp.set_header('Content-Type', 'text/plain')
            resp.set_headers(headers)

    falcon_app.add_route(path, HelloResource())

    return falcon_app


def create_wheezy(body, headers, path):
    def hello(request):
        response = wheezy.HTTPResponse(content_type='text/plain')
        response.write_bytes(body)
        response.headers.extend(headers.items())

        return response

    def router(request, following):
        if path == request.path:
            response = hello(request)
        else:
            response = wheezy.not_found()

        return response

    return wheezy.WSGIApplication([
        wheezy.bootstrap_http_defaults,
        lambda ignore: router
    ], {})


def create_flask(body, headers, path):
    flask_app = flask.Flask('hello')

    @flask_app.route(path)
    def hello():
        return flask.Response(data=body, headers=headers,
                              mimetype='text/plain')

    return flask_app


def create_bottle(body, headers, path):
    @bottle.route(path)
    def hello():
        return bottle.Response(body, headers=headers)

    return bottle.default_app()


def create_werkzeug(body, headers, path):
    url_map = Map([Rule(path)])

    @werkzeug.Request.application
    def hello(request):
        adapter = url_map.bind_to_environ(request.environ)
        endpoint, values = adapter.match()
        return werkzeug.Response(body, headers=headers,
                                 mimetype='text/plain')

    return hello


def create_pecan(body, headers, path):
    return nuts.create()


def avg(array):
    return sum(array) / len(array)


def bench(name):
    iterations = 100000

    func = create_bench(name)
    results = repeat(func, number=iterations)

    sec_per_req = avg(results) / iterations

    sys.stdout.write('.')
    sys.stdout.flush()

    return (name, sec_per_req)


def create_bench(name):
    path = '/hello/test'
    srmock = helpers.StartResponseMock()
    env = helpers.create_environ(path)
    body = helpers.rand_string(10240, 10240)
    headers = {'X-Test': 'Funky Chicken'}

    app = eval('create_{0}(body, headers, path)'.format(name.lower()))

    def bench():
        app(env, srmock)

    return bench


if __name__ == '__main__':
    sys.stdout.write('\nBenchmarking')
    sys.stdout.flush()
    results = [bench(framework) for framework in [
        'Wheezy', 'Flask', 'Werkzeug', 'Falcon', 'Pecan', 'Bottle']
    ]
    """
    results = [bench(framework) for framework in [
        'Falcon']
    ]
    """

    print('done.\n')

    results = sorted(results, key=lambda r: r[1])
    for i, (name, sec_per_req) in enumerate(results):
        req_per_sec = 1 / sec_per_req
        ms_per_req = sec_per_req * 1000
        print('{3}. {0:.<15s}{1:.>06,.0f} req/sec or {2:0.2f} ms/req'.
              format(name, req_per_sec, ms_per_req, i + 1))

    print('')
