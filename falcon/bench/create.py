import sys
import re

import wheezy.http as wheezy
from wheezy.core.collections import last_item_adapter
import bottle

import flask
import werkzeug.wrappers as werkzeug
from werkzeug.routing import Map, Rule

sys.path.append('./nuts/nuts')
import app as nuts
del sys.path[-1]

sys.path.append('../..')
import falcon
del sys.path[-1]


def create_falcon(body, headers):
    path = '/hello/{account_id}/test'
    falcon_app = falcon.API()

    class HelloResource:
        def on_get(self, req, resp, account_id):
            limit = req.get_param('limit', '10')
            resp.body = body
            resp.set_header('Content-Type', 'text/plain')
            resp.set_headers(headers)

    falcon_app.add_route(path, HelloResource())

    return falcon_app


def create_wheezy(body, headers):
    def hello(request, account_id):
        query = last_item_adapter(request.query)

        try:
            limit = query['limit']
        except KeyError:
            limit = '10'

        response = wheezy.HTTPResponse(content_type='text/plain')
        response.write_bytes(body)
        response.headers.extend(headers.items())

        return response

    # Convert Level 1 var patterns to equivalent named regex groups
    path = '/hello/{account_id}/test'
    pattern = re.sub(r'{([a-zA-Z][a-zA-Z_]*)}', r'(?P<\1>[^/]+)', path)
    pattern = r'\A' + pattern + r'\Z'
    matcher = re.compile(pattern, re.IGNORECASE)

    def router(request, following):
        match = matcher.match(request.path)
        if match:
            # A real router would probably have to get all named params
            params = match.groupdict()

            response = hello(request, **params)
        else:
            response = wheezy.not_found()

        return response

    return wheezy.WSGIApplication([
        wheezy.bootstrap_http_defaults,
        lambda ignore: router
    ], {})


def create_flask(body, headers):
    path = '/hello/<account_id>/test'
    flask_app = flask.Flask('hello')

    @flask_app.route(path)
    def hello(account_id):
        flask.request.args.get('limit', '10')
        return flask.Response(body, headers=headers,
                              mimetype='text/plain')

    return flask_app


def create_bottle(body, headers):
    path = '/hello/<account_id>/test'

    @bottle.route(path)
    def hello(account_id):
        limit = bottle.request.query.limit or '10'
        return bottle.Response(body, headers=headers)

    return bottle.default_app()


def create_werkzeug(body, headers):
    path = '/hello/<account_id>/test'
    url_map = Map([Rule(path, endpoint='hello')])

    @werkzeug.Request.application
    def hello(request):
        limit = request.args.get('limit', '10')
        adapter = url_map.bind_to_environ(request.environ)
        endpoint, values = adapter.match()
        return werkzeug.Response(body, headers=headers,
                                 mimetype='text/plain')

    return hello


def create_pecan(body, headers):
    return nuts.create()
