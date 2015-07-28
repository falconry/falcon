.. _quickstart:

Quickstart
==========

If you haven't done so already, please take a moment to
:ref:`install <install>` the Falcon web framework before
continuing.


.. include:: big-picture-snip.rst


Learning by Example
-------------------

Here is a simple example from Falcon's README, showing how to get
started writing an API:

.. code:: python

    # things.py

    # Let's get this party started
    import falcon


    # Falcon follows the REST architectural style, meaning (among
    # other things) that you think in terms of resources and state
    # transitions, which map to HTTP verbs.
    class ThingsResource:
        def on_get(self, req, resp):
            """Handles GET requests"""
            resp.status = falcon.HTTP_200  # This is the default status
            resp.body = ('\nTwo things awe me most, the starry sky '
                         'above me and the moral law within me.\n'
                         '\n'
                         '    ~ Immanuel Kant\n\n')

    # falcon.API instances are callable WSGI apps
    app = falcon.API()

    # Resources are represented by long-lived class instances
    things = ThingsResource()

    # things will handle all requests to the '/things' URL path
    app.add_route('/things', things)

You can run the above example using any WSGI server, such as uWSGI
or Gunicorn. For example:

.. code:: bash

    $ pip install gunicorn
    $ gunicorn things:app

Then, in another terminal:

.. code:: bash

    $ curl localhost:8000/things

.. _quickstart-more-features:

More Features
-------------

Here is a more involved example that demonstrates reading headers and query
parameters, handling errors, and working with request and response bodies.

.. code:: python

    import json
    import logging
    import uuid
    from wsgiref import simple_server

    import falcon
    import requests


    class StorageEngine(object):

        def get_things(self, marker, limit):
            return [{'id': str(uuid.uuid4()), 'color': 'green'}]

        def add_thing(self, thing):
            thing['id'] = str(uuid.uuid4())
            return thing


    class StorageError(Exception):

        @staticmethod
        def handle(ex, req, resp, params):
            description = ('Sorry, couldn\'t write your thing to the '
                           'database. It worked on my box.')

            raise falcon.HTTPError(falcon.HTTP_725,
                                   'Database Error',
                                   description)


    class SinkAdapter(object):

        engines = {
            'ddg': 'https://duckduckgo.com',
            'y': 'https://search.yahoo.com/search',
        }

        def __call__(self, req, resp, engine):
            url = self.engines[engine]
            params = {'q': req.get_param('q', True)}
            result = requests.get(url, params=params)

            resp.status = str(result.status_code) + ' ' + result.reason
            resp.content_type = result.headers['content-type']
            resp.body = result.text


    class AuthMiddleware(object):

        def process_request(self, req, resp):
            token = req.get_header('X-Auth-Token')
            project = req.get_header('X-Project-ID')

            if token is None:
                description = ('Please provide an auth token '
                               'as part of the request.')

                raise falcon.HTTPUnauthorized('Auth token required',
                                              description,
                                              href='http://docs.example.com/auth')

            if not self._token_is_valid(token, project):
                description = ('The provided auth token is not valid. '
                               'Please request a new token and try again.')

                raise falcon.HTTPUnauthorized('Authentication required',
                                              description,
                                              href='http://docs.example.com/auth',
                                              scheme='Token; UUID')

        def _token_is_valid(self, token, project):
            return True  # Suuuuuure it's valid...


    class RequireJSON(object):

        def process_request(self, req, resp):
            if not req.client_accepts_json:
                raise falcon.HTTPNotAcceptable(
                    'This API only supports responses encoded as JSON.',
                    href='http://docs.examples.com/api/json')

            if req.method in ('POST', 'PUT'):
                if 'application/json' not in req.content_type:
                    raise falcon.HTTPUnsupportedMediaType(
                        'This API only supports requests encoded as JSON.',
                        href='http://docs.examples.com/api/json')


    class JSONTranslator(object):

        def process_request(self, req, resp):
            # req.stream corresponds to the WSGI wsgi.input environ variable,
            # and allows you to read bytes from the request body.
            #
            # See also: PEP 3333
            if req.content_length in (None, 0):
                # Nothing to do
                return

            body = req.stream.read()
            if not body:
                raise falcon.HTTPBadRequest('Empty request body',
                                            'A valid JSON document is required.')

            try:
                req.context['doc'] = json.loads(body.decode('utf-8'))

            except (ValueError, UnicodeDecodeError):
                raise falcon.HTTPError(falcon.HTTP_753,
                                       'Malformed JSON',
                                       'Could not decode the request body. The '
                                       'JSON was incorrect or not encoded as '
                                       'UTF-8.')

        def process_response(self, req, resp, resource):
            if 'result' not in req.context:
                return

            resp.body = json.dumps(req.context['result'])


    def max_body(limit):

        def hook(req, resp, resource, params):
            length = req.content_length
            if length is not None and length > limit:
                msg = ('The size of the request is too large. The body must not '
                       'exceed ' + str(limit) + ' bytes in length.')

                raise falcon.HTTPRequestEntityTooLarge(
                    'Request body is too large', msg)

        return hook


    class ThingsResource:

        def __init__(self, db):
            self.db = db
            self.logger = logging.getLogger('thingsapp.' + __name__)

        def on_get(self, req, resp, user_id):
            marker = req.get_param('marker') or ''
            limit = req.get_param_as_int('limit') or 50

            try:
                result = self.db.get_things(marker, limit)
            except Exception as ex:
                self.logger.error(ex)

                description = ('Aliens have attacked our base! We will '
                               'be back as soon as we fight them off. '
                               'We appreciate your patience.')

                raise falcon.HTTPServiceUnavailable(
                    'Service Outage',
                    description,
                    30)

            # An alternative way of doing DRY serialization would be to
            # create a custom class that inherits from falcon.Request. This
            # class could, for example, have an additional 'doc' property
            # that would serialize to JSON under the covers.
            req.context['result'] = result

            resp.set_header('X-Powered-By', 'Small Furry Creatures')
            resp.status = falcon.HTTP_200

        @falcon.before(max_body(64 * 1024))
        def on_post(self, req, resp, user_id):
            try:
                doc = req.context['doc']
            except KeyError:
                raise falcon.HTTPBadRequest(
                    'Missing thing',
                    'A thing must be submitted in the request body.')

            proper_thing = self.db.add_thing(doc)

            resp.status = falcon.HTTP_201
            resp.location = '/%s/things/%s' % (user_id, proper_thing['id'])


    # Configure your WSGI server to load "things.app" (app is a WSGI callable)
    app = falcon.API(middleware=[
        AuthMiddleware(),
        RequireJSON(),
        JSONTranslator(),
    ])

    db = StorageEngine()
    things = ThingsResource(db)
    app.add_route('/{user_id}/things', things)

    # If a responder ever raised an instance of StorageError, pass control to
    # the given handler.
    app.add_error_handler(StorageError, StorageError.handle)

    # Proxy some things to another service; this example shows how you might
    # send parts of an API off to a legacy system that hasn't been upgraded
    # yet, or perhaps is a single cluster that all data centers have to share.
    sink = SinkAdapter()
    app.add_sink(sink, r'/search/(?P<engine>ddg|y)\Z')

    # Useful for debugging problems in your API; works with pdb.set_trace()
    if __name__ == '__main__':
        httpd = simple_server.make_server('127.0.0.1', 8000, app)
        httpd.serve_forever()
