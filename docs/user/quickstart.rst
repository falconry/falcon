.. _quickstart:

Quickstart
==========

If you haven't done so already, please take a moment to
:ref:`install <install>` the Falcon web framework before
continuing.

Learning by Example
-------------------

Here is a simple example from Falcon's README, showing how to get
started writing an app.

.. tabs::

    .. group-tab:: WSGI

        .. code:: python

            # examples/things.py

            # Let's get this party started!
            from wsgiref.simple_server import make_server

            import falcon


            # Falcon follows the REST architectural style, meaning (among
            # other things) that you think in terms of resources and state
            # transitions, which map to HTTP verbs.
            class ThingsResource:
                def on_get(self, req, resp):
                    """Handles GET requests"""
                    resp.status = falcon.HTTP_200  # This is the default status
                    resp.content_type = falcon.MEDIA_TEXT  # Default is JSON, so override
                    resp.text = ('\nTwo things awe me most, the starry sky '
                                 'above me and the moral law within me.\n'
                                 '\n'
                                 '    ~ Immanuel Kant\n\n')


            # falcon.App instances are callable WSGI apps
            # in larger applications the app is created in a separate file
            app = falcon.App()

            # Resources are represented by long-lived class instances
            things = ThingsResource()

            # things will handle all requests to the '/things' URL path
            app.add_route('/things', things)

            if __name__ == '__main__':
                with make_server('', 8000, app) as httpd:
                    print('Serving on port 8000...')

                    # Serve until process is killed
                    httpd.serve_forever()

        You can run the above example directly using the included wsgiref server:

        .. code:: bash

            $ pip install falcon
            $ python things.py

        Then, in another terminal:

        .. code:: bash

            $ curl localhost:8000/things

        As an alternative to Curl, you might want to give
        `HTTPie <https://github.com/jkbr/httpie>`_ a try:

        .. code:: bash

            $ pip install --upgrade httpie
            $ http localhost:8000/things

    .. group-tab:: ASGI

        .. code:: python

            # examples/things_asgi.py

            import falcon
            import falcon.asgi


            # Falcon follows the REST architectural style, meaning (among
            # other things) that you think in terms of resources and state
            # transitions, which map to HTTP verbs.
            class ThingsResource:
                async def on_get(self, req, resp):
                    """Handles GET requests"""
                    resp.status = falcon.HTTP_200  # This is the default status
                    resp.content_type = falcon.MEDIA_TEXT  # Default is JSON, so override
                    resp.text = ('\nTwo things awe me most, the starry sky '
                                 'above me and the moral law within me.\n'
                                 '\n'
                                 '    ~ Immanuel Kant\n\n')


            # falcon.asgi.App instances are callable ASGI apps...
            # in larger applications the app is created in a separate file
            app = falcon.asgi.App()

            # Resources are represented by long-lived class instances
            things = ThingsResource()

            # things will handle all requests to the '/things' URL path
            app.add_route('/things', things)

        You can run the ASGI version with uvicorn or any other ASGI server:

        .. code:: bash

            $ pip install falcon uvicorn
            $ uvicorn things_asgi:app

        Then, in another terminal:

        .. code:: bash

            $ curl localhost:8000/things

        As an alternative to Curl, you might want to give
        `HTTPie <https://github.com/jkbr/httpie>`_ a try:

        .. code:: bash

            $ pip install --upgrade httpie
            $ http localhost:8000/things

.. _quickstart-more-features:

A More Complex Example
----------------------

Here is a more involved example that demonstrates reading headers and query
parameters, handling errors, and working with request and response bodies.

.. tabs::

    .. group-tab:: WSGI

        Note that this example assumes that the
        `requests <https://pypi.org/project/requests/>`_ package has been installed.

        .. code:: python

            # examples/things_advanced.py

            import json
            import logging
            import uuid
            from wsgiref import simple_server

            import falcon
            import requests


            class StorageEngine:

                def get_things(self, marker, limit):
                    return [{'id': str(uuid.uuid4()), 'color': 'green'}]

                def add_thing(self, thing):
                    thing['id'] = str(uuid.uuid4())
                    return thing


            class StorageError(Exception):

                @staticmethod
                def handle(ex, req, resp, params):
                    # TODO: Log the error, clean up, etc. before raising
                    raise falcon.HTTPInternalServerError()


            class SinkAdapter:

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
                    resp.text = result.text


            class AuthMiddleware:

                def process_request(self, req, resp):
                    token = req.get_header('Authorization')
                    account_id = req.get_header('Account-ID')

                    challenges = ['Token type="Fernet"']

                    if token is None:
                        description = ('Please provide an auth token '
                                       'as part of the request.')

                        raise falcon.HTTPUnauthorized(title='Auth token required',
                                                      description=description,
                                                      challenges=challenges,
                                                      href='http://docs.example.com/auth')

                    if not self._token_is_valid(token, account_id):
                        description = ('The provided auth token is not valid. '
                                       'Please request a new token and try again.')

                        raise falcon.HTTPUnauthorized(title='Authentication required',
                                                      description=description,
                                                      challenges=challenges,
                                                      href='http://docs.example.com/auth')

                def _token_is_valid(self, token, account_id):
                    return True  # Suuuuuure it's valid...


            class RequireJSON:

                def process_request(self, req, resp):
                    if not req.client_accepts_json:
                        raise falcon.HTTPNotAcceptable(
                            description='This API only supports responses encoded as JSON.',
                            href='http://docs.examples.com/api/json')

                    if req.method in ('POST', 'PUT'):
                        if 'application/json' not in req.content_type:
                            raise falcon.HTTPUnsupportedMediaType(
                                title='This API only supports requests encoded as JSON.',
                                href='http://docs.examples.com/api/json')


            class JSONTranslator:
                # NOTE: Normally you would simply use req.media and resp.media for
                # this particular use case; this example serves only to illustrate
                # what is possible.

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
                        raise falcon.HTTPBadRequest(title='Empty request body',
                                                    description='A valid JSON document is required.')

                    try:
                        req.context.doc = json.loads(body.decode('utf-8'))

                    except (ValueError, UnicodeDecodeError):
                        description = ('Could not decode the request body. The '
                                       'JSON was incorrect or not encoded as '
                                       'UTF-8.')

                        raise falcon.HTTPBadRequest(title='Malformed JSON',
                                                    description=description)

                def process_response(self, req, resp, resource, req_succeeded):
                    if not hasattr(resp.context, 'result'):
                        return

                    resp.text = json.dumps(resp.context.result)


            def max_body(limit):

                def hook(req, resp, resource, params):
                    length = req.content_length
                    if length is not None and length > limit:
                        msg = ('The size of the request is too large. The body must not '
                               'exceed ' + str(limit) + ' bytes in length.')

                        raise falcon.HTTPPayloadTooLarge(
                            title='Request body is too large', description=msg)

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
                            title='Service Outage',
                            description=description,
                            retry_after=30)

                    # NOTE: Normally you would use resp.media for this sort of thing;
                    # this example serves only to demonstrate how the context can be
                    # used to pass arbitrary values between middleware components,
                    # hooks, and resources.
                    resp.context.result = result

                    resp.set_header('Powered-By', 'Falcon')
                    resp.status = falcon.HTTP_200

                @falcon.before(max_body(64 * 1024))
                def on_post(self, req, resp, user_id):
                    try:
                        doc = req.context.doc
                    except AttributeError:
                        raise falcon.HTTPBadRequest(
                            title='Missing thing',
                            description='A thing must be submitted in the request body.')

                    proper_thing = self.db.add_thing(doc)

                    resp.status = falcon.HTTP_201
                    resp.location = '/%s/things/%s' % (user_id, proper_thing['id'])


            # Configure your WSGI server to load "things.app" (app is a WSGI callable)
            app = falcon.App(middleware=[
                AuthMiddleware(),
                RequireJSON(),
                JSONTranslator(),
            ])

            db = StorageEngine()
            things = ThingsResource(db)
            app.add_route('/{user_id}/things', things)

            # If a responder ever raises an instance of StorageError, pass control to
            # the given handler.
            app.add_error_handler(StorageError, StorageError.handle)

            # Proxy some things to another service; this example shows how you might
            # send parts of an API off to a legacy system that hasn't been upgraded
            # yet, or perhaps is a single cluster that all data centers have to share.
            sink = SinkAdapter()
            app.add_sink(sink, r'/search/(?P<engine>ddg|y)\Z')

            # Useful for debugging problems in your API; works with pdb.set_trace(). You
            # can also use Gunicorn to host your app. Gunicorn can be configured to
            # auto-restart workers when it detects a code change, and it also works
            # with pdb.
            if __name__ == '__main__':
                httpd = simple_server.make_server('127.0.0.1', 8000, app)
                httpd.serve_forever()

        Again this code uses wsgiref, but you can also run the above example using
        any WSGI server, such as uWSGI or Gunicorn. For example:

        .. code:: bash

            $ pip install requests gunicorn
            $ gunicorn things:app

        On Windows you can run Gunicorn and uWSGI via WSL, or you might try Waitress:

        .. code:: bash

            $ pip install requests waitress
            $ waitress-serve --port=8000 things:app


        To test this example go to the another terminal and run:

        .. code:: bash

            $ http localhost:8000/1/things authorization:custom-token

        To visualize the application configuration the :ref:`inspect` can be used:

        .. code:: bash

            falcon-inspect-app things_advanced:app

        This would print for this example application:

        .. code::

            Falcon App (WSGI)
            • Routes:
                ⇒ /{user_id}/things - ThingsResource:
                   ├── GET - on_get
                   └── POST - on_post
            • Middleware (Middleware are independent):
                → AuthMiddleware.process_request
                  → RequireJSON.process_request
                    → JSONTranslator.process_request

                        ├── Process route responder

                    ↢ JSONTranslator.process_response
            • Sinks:
                ⇥ /search/(?P<engine>ddg|y)\Z SinkAdapter
            • Error handlers:
                ⇜ StorageError handle

    .. group-tab:: ASGI

        Note that this example requires the
        `httpx <https://pypi.org/project/httpx/>`_ package in lieu of
        `requests <https://pypi.org/project/requests/>`_.

        .. code:: python

            # examples/things_advanced_asgi.py

            import json
            import logging
            import uuid

            import falcon
            import falcon.asgi
            import httpx


            class StorageEngine:

                async def get_things(self, marker, limit):
                    return [{'id': str(uuid.uuid4()), 'color': 'green'}]

                async def add_thing(self, thing):
                    thing['id'] = str(uuid.uuid4())
                    return thing


            class StorageError(Exception):

                @staticmethod
                async def handle(ex, req, resp, params):
                    # TODO: Log the error, clean up, etc. before raising
                    raise falcon.HTTPInternalServerError()


            class SinkAdapter:

                engines = {
                    'ddg': 'https://duckduckgo.com',
                    'y': 'https://search.yahoo.com/search',
                }

                async def __call__(self, req, resp, engine):
                    url = self.engines[engine]
                    params = {'q': req.get_param('q', True)}

                    async with httpx.AsyncClient() as client:
                        result = await client.get(url, params=params)

                    resp.status = result.status_code
                    resp.content_type = result.headers['content-type']
                    resp.text = result.text


            class AuthMiddleware:

                async def process_request(self, req, resp):
                    token = req.get_header('Authorization')
                    account_id = req.get_header('Account-ID')

                    challenges = ['Token type="Fernet"']

                    if token is None:
                        description = ('Please provide an auth token '
                                       'as part of the request.')

                        raise falcon.HTTPUnauthorized(title='Auth token required',
                                                      description=description,
                                                      challenges=challenges,
                                                      href='http://docs.example.com/auth')

                    if not self._token_is_valid(token, account_id):
                        description = ('The provided auth token is not valid. '
                                       'Please request a new token and try again.')

                        raise falcon.HTTPUnauthorized(title='Authentication required',
                                                      description=description,
                                                      challenges=challenges,
                                                      href='http://docs.example.com/auth')

                def _token_is_valid(self, token, account_id):
                    return True  # Suuuuuure it's valid...


            class RequireJSON:

                async def process_request(self, req, resp):
                    if not req.client_accepts_json:
                        raise falcon.HTTPNotAcceptable(
                            description='This API only supports responses encoded as JSON.',
                            href='http://docs.examples.com/api/json')

                    if req.method in ('POST', 'PUT'):
                        if 'application/json' not in req.content_type:
                            raise falcon.HTTPUnsupportedMediaType(
                                description='This API only supports requests encoded as JSON.',
                                href='http://docs.examples.com/api/json')


            class JSONTranslator:
                # NOTE: Normally you would simply use req.get_media() and resp.media for
                # this particular use case; this example serves only to illustrate
                # what is possible.

                async def process_request(self, req, resp):
                    # NOTE: Test explicitly for 0, since this property could be None in
                    # the case that the Content-Length header is missing (in which case we
                    # can't know if there is a body without actually attempting to read
                    # it from the request stream.)
                    if req.content_length == 0:
                        # Nothing to do
                        return

                    body = await req.stream.read()
                    if not body:
                        raise falcon.HTTPBadRequest(title='Empty request body',
                                                    description='A valid JSON document is required.')

                    try:
                        req.context.doc = json.loads(body.decode('utf-8'))

                    except (ValueError, UnicodeDecodeError):
                        description = ('Could not decode the request body. The '
                                       'JSON was incorrect or not encoded as '
                                       'UTF-8.')

                        raise falcon.HTTPBadRequest(title='Malformed JSON',
                                                    description=description)

                async def process_response(self, req, resp, resource, req_succeeded):
                    if not hasattr(resp.context, 'result'):
                        return

                    resp.text = json.dumps(resp.context.result)


            def max_body(limit):

                async def hook(req, resp, resource, params):
                    length = req.content_length
                    if length is not None and length > limit:
                        msg = ('The size of the request is too large. The body must not '
                               'exceed ' + str(limit) + ' bytes in length.')

                        raise falcon.HTTPPayloadTooLarge(
                            title='Request body is too large', description=msg)

                return hook


            class ThingsResource:

                def __init__(self, db):
                    self.db = db
                    self.logger = logging.getLogger('thingsapp.' + __name__)

                async def on_get(self, req, resp, user_id):
                    marker = req.get_param('marker') or ''
                    limit = req.get_param_as_int('limit') or 50

                    try:
                        result = await self.db.get_things(marker, limit)
                    except Exception as ex:
                        self.logger.error(ex)

                        description = ('Aliens have attacked our base! We will '
                                       'be back as soon as we fight them off. '
                                       'We appreciate your patience.')

                        raise falcon.HTTPServiceUnavailable(
                            title='Service Outage',
                            description=description,
                            retry_after=30)

                    # NOTE: Normally you would use resp.media for this sort of thing;
                    # this example serves only to demonstrate how the context can be
                    # used to pass arbitrary values between middleware components,
                    # hooks, and resources.
                    resp.context.result = result

                    resp.set_header('Powered-By', 'Falcon')
                    resp.status = falcon.HTTP_200

                @falcon.before(max_body(64 * 1024))
                async def on_post(self, req, resp, user_id):
                    try:
                        doc = req.context.doc
                    except AttributeError:
                        raise falcon.HTTPBadRequest(
                            title='Missing thing',
                            description='A thing must be submitted in the request body.')

                    proper_thing = await self.db.add_thing(doc)

                    resp.status = falcon.HTTP_201
                    resp.location = '/%s/things/%s' % (user_id, proper_thing['id'])


            # The app instance is an ASGI callable
            app = falcon.asgi.App(middleware=[
                # AuthMiddleware(),
                RequireJSON(),
                JSONTranslator(),
            ])

            db = StorageEngine()
            things = ThingsResource(db)
            app.add_route('/{user_id}/things', things)

            # If a responder ever raises an instance of StorageError, pass control to
            # the given handler.
            app.add_error_handler(StorageError, StorageError.handle)

            # Proxy some things to another service; this example shows how you might
            # send parts of an API off to a legacy system that hasn't been upgraded
            # yet, or perhaps is a single cluster that all data centers have to share.
            sink = SinkAdapter()
            app.add_sink(sink, r'/search/(?P<engine>ddg|y)\Z')

        You can run the ASGI version with any ASGI server, such as uvicorn:

        .. code:: bash

            $ pip install falcon httpx uvicorn
            $ uvicorn things_advanced_asgi:app
