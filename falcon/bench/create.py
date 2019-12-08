# Copyright 2014 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys


def falcon(body, headers):
    import falcon

    path = '/hello/{account_id}/test'
    falcon_app = falcon.App('text/plain')

    # def ask(req, resp, params):
    #     params['answer'] = 42

    # @falcon.before(ask)
    class HelloResource:
        def on_get(self, req, resp, account_id):
            user_agent = req.user_agent  # NOQA
            limit = req.get_param('limit') or '10'  # NOQA
            resp.data = body
            resp.set_headers(headers)

    falcon_app.add_route(path, HelloResource())

    return falcon_app


def falcon_ext(body, headers):
    from falcon.bench.queues import api
    return api.create(body, headers)


def flask(body, headers):
    import flask

    path = '/hello/<account_id>/test'
    flask_app = flask.Flask('hello')

    @flask_app.route(path)
    def hello(account_id):
        request = flask.request
        user_agent = request.headers['User-Agent']  # NOQA
        limit = request.args.get('limit', '10')  # NOQA

        return flask.Response(body, headers=headers,
                              mimetype='text/plain')

    return flask_app


def bottle(body, headers):
    import bottle
    path = '/hello/<account_id>/test'

    @bottle.route(path)
    def hello(account_id):
        user_agent = bottle.request.headers['User-Agent']  # NOQA
        limit = bottle.request.query.limit or '10'  # NOQA

        for header in headers.items():
            bottle.response.set_header(*header)

        return body

    return bottle.default_app()


def werkzeug(body, headers):
    import werkzeug.wrappers as werkzeug
    from werkzeug.routing import Map, Rule

    path = '/hello/<account_id>/test'
    url_map = Map([Rule(path, endpoint='hello')])

    @werkzeug.Request.application
    def hello(request):
        user_agent = request.headers['User-Agent']  # NOQA
        limit = request.args.get('limit', '10')  # NOQA
        adapter = url_map.bind_to_environ(request.environ)  # NOQA
        endpoint, values = adapter.match()  # NOQA
        aid = values['account_id']  # NOQA

        return werkzeug.Response(body, headers=headers,
                                 mimetype='text/plain')

    return hello


def pecan(body, headers):
    import pecan
    pecan.x_test_body = body
    pecan.x_test_headers = headers

    import falcon.bench.nuts.nuts.app as nuts
    sys.path.append(os.path.dirname(nuts.__file__))
    app = nuts.create()
    del sys.path[-1]

    return app


def django(body, headers):
    import django
    django.x_test_body = body
    django.x_test_headers = headers

    from falcon.bench import dj
    sys.path.append(os.path.dirname(dj.__file__))

    from falcon.bench.dj.dj import wsgi
    return wsgi.application
