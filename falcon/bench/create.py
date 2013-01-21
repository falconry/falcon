import sys

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
