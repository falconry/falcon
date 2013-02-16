import sys
import re
import six


def create_falcon(body, headers):
    sys.path.append('..')
    import falcon
    del sys.path[-1]

    path = '/hello/{account_id}/test'
    falcon_app = falcon.API('text/plain')

    def ask(req, resp, params):
        params['answer'] = 42

    # @falcon.before(ask)
    class HelloResource:
        def on_get(self, req, resp, account_id):
            user_agent = req.user_agent  # NOQA
            limit = req.get_param('limit', '10')  # NOQA
            if six.PY3:
                resp.body = body
            else:
                resp.data = body

            # resp.vary = ['accept-encoding', 'x-auth-token']
            #resp.content_range = (0, 499, 10240)

            resp.set_headers(headers)

    falcon_app.add_route(path, HelloResource())

    return falcon_app


def create_wheezy(body, headers):
    import wheezy.http as wheezy
    from wheezy.core.collections import last_item_adapter

    def hello(request, account_id):
        query = last_item_adapter(request.query)

        try:
            limit = query['limit']
        except KeyError:
            limit = '10'  # NOQA

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


def create_bottle(body, headers):
    import bottle
    path = '/hello/<account_id>/test'

    @bottle.route(path)
    def hello(account_id):
        user_agent = bottle.request.headers['User-Agent']  # NOQA
        limit = bottle.request.query.limit or '10'  # NOQA

        return bottle.Response(body, headers=headers)

    return bottle.default_app()


def create_werkzeug(body, headers):
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

        return werkzeug.Response(body, headers=headers,
                                 mimetype='text/plain')

    return hello


def create_cherrypy(body, headers):
    import cherrypy

    # Disable logging
    cherrypy.config.update({'environment': 'embedded'})

    class HelloResource(object):

        exposed = True

        def GET(self, account_id, test, limit=8):
            user_agent = cherrypy.request.headers['User-Agent']  # NOQA
            for name, value in headers.items():
                cherrypy.response.headers[name] = value

            return body

    class Root(object):
        pass

    root = Root()
    root.hello = HelloResource()

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        }
    }

    app = cherrypy.tree.mount(root, '/', conf)
    return app


def create_pecan(body, headers):
    sys.path.append('./nuts/nuts')
    import app as nuts
    del sys.path[-1]

    return nuts.create()
