.. _faq:

FAQ
===

Design Philosophy
~~~~~~~~~~~~~~~~~

Why doesn't Falcon come with batteries included?
------------------------------------------------
Falcon is designed for applications that require a high level of
customization or performance tuning. The framework's minimalist design
frees the developer to select the best strategies and 3rd-party
packages for the task at hand.

The Python ecosystem offers a number of great packages that you can
use from within your responders, hooks, and middleware components. As
a starting point, the community maintains a list of `Falcon add-ons
and complementary packages <https://github.com/falconry/falcon/wiki>`_.

Why doesn't Falcon create a new Resource instance for every request?
--------------------------------------------------------------------
Falcon generally tries to minimize the number of objects that it
instantiates. It does this for two reasons: first, to avoid the expense of
creating the object, and second to reduce memory usage by reducing the
total number of objects required under highly concurrent workloads. Therefore,
when adding a route, Falcon requires an *instance* of your resource class,
rather than the class type. That same instance will be used to serve all
requests coming in on that route.

What happens if my responder raises an error?
---------------------------------------------
Generally speaking, Falcon assumes that resource responders (such as
``on_get()``, ``on_post()``, etc.) will, for the most part, do the right thing.
In other words, Falcon doesn't try very hard to protect responder code from
itself.

.. note::
    As of version 3.0, the framework will no longer propagate uncaught
    exceptions to the application server.
    Instead, the default ``Exception`` handler will return an HTTP 500 response
    and log details of the exception to ``wsgi.errors``.

Although providing basic error handlers, Falcon optimizes for the most common
case where resource responders do not raise any errors for valid requests.
With that in mind, writing a high-quality API based on Falcon requires that:

#. Resource responders set response variables to sane values.
#. Your code is well-tested, with high code coverage.
#. Errors are anticipated, detected, and handled appropriately within
   each responder and with the aid of custom error handlers.

How do I generate API documentation for my Falcon API?
------------------------------------------------------
When it comes to API documentation, some developers prefer to use the API
implementation as the user contract or source of truth (taking an
implementation-first approach), while other developers prefer to use the API
spec itself as the contract, implementing and testing the API against that spec
(taking a design-first approach).

At the risk of erring on the side of flexibility, Falcon does not provide API
spec support out of the box. However, there are several community projects
available in this vein. Our
`Add on Catalog <https://github.com/falconry/falcon/wiki/Add-on-Catalog>`_ lists
a couple of these projects, but you may also wish to search
`PyPI <https://pypi.python.org/pypi>`_ for additional packages.

If you are interested in the design-first approach mentioned above, you may
also want to check out API design and gateway services such as Tyk, Apiary,
Amazon API Gateway, or Google Cloud Endpoints.

Performance
~~~~~~~~~~~

Does Falcon work with HTTP/2?
-----------------------------

Falcon is a WSGI framework and as such does not serve HTTP requests directly.
However, you can get most of the benefits of HTTP/2 by simply deploying any
HTTP/2-compliant web server or load balancer in front of your app to translate
between HTTP/2 and HTTP/1.1. Eventually we expect that Python web servers (such
as uWSGI) will support HTTP/2 natively, eliminating the need for a translation
layer.

.. _faq_thread_safety:

Is Falcon thread-safe?
----------------------

The Falcon framework is, itself, thread-safe. For example, new
:class:`~falcon.Request` and :class:`~falcon.Response` objects are created
for each incoming HTTP request. However, a single instance of each resource
class attached to a route is shared among all requests. Middleware objects and
other types of hooks, such as custom error handlers, are likewise shared.
Therefore, as long as you implement these classes and callables in a
thread-safe manner, and ensure that any third-party libraries used by your
app are also thread-safe, your WSGI app as a whole will be thread-safe.

.. _faq_free_threading:

Can I run Falcon on free-threaded CPython?
------------------------------------------

At the time of this writing, Falcon has not been extensively evaluated without
the GIL yet.

We load-tested the WSGI flavor of the framework via
:class:`~wsgiref.simple_server.WSGIServer` +
:class:`~socketserver.ThreadingMixIn` on
`free-threaded CPython 3.13.0
<https://docs.python.org/3.13/whatsnew/3.13.html#free-threaded-cpython>`__
(under ``PYTHON_GIL=0``), and observed no issues that would point toward
Falcon's reliance on the GIL. Thus, we would like to think that Falcon is still
:ref:`thread-safe <faq_thread_safety>` even in free-threaded execution,
but it is too early to provide a definite answer.

If you experimented with free-threading of Falcon or other Python web services,
please :ref:`share your experience <chat>`!

Does Falcon support asyncio?
------------------------------

Starting with version 3.0, the `ASGI <https://asgi.readthedocs.io/en/latest/>`_
flavor of Falcon now proudly supports :any:`asyncio`!
Use the :class:`falcon.asgi.App` class to create an async application, and
serve it via an :ref:`ASGI application server <install_asgi_server>` such as
Uvicorn.

Alternatively, IO-bound WSGI applications can be scaled using the battle-tested
`gevent <http://www.gevent.org/>`_ library via Gunicorn or uWSGI.
`meinheld <https://pypi.org/project/meinheld/>`_ has also been used
successfully by the community to power high-throughput, low-latency WSGI
services.

.. tip::
    Note that if you use Gunicorn, you can combine gevent and PyPy to achieve
    an impressive level of performance.
    (Unfortunately, uWSGI does not yet support using gevent and PyPy together.)

Does Falcon support WebSocket?
------------------------------

The async flavor of Falcon supports the
`ASGI <https://asgi.readthedocs.io/en/latest/>`_ WebSocket protocol.
See also: :ref:`ws`.

WSGI applications might try leveraging
`uWSGI's native WebSocket support <http://uwsgi.readthedocs.io/en/latest/WebSockets.html>`_
or `gevent-websocket's <https://pypi.org/project/gevent-websocket>`_
``GeventWebSocketWorker`` for Gunicorn.

As an option, it may make sense to design WebSocket support as a separate
service due to very different performance characteristics and interaction
patterns, compared to a regular RESTful API. In addition to (obviously!)
Falcon's native ASGI support, a standalone WebSocket service could also be
implemented via Aymeric Augustin's handy
`websockets <https://pypi.python.org/pypi/websockets>`_ library.

Routing
~~~~~~~

How do I implement CORS with Falcon?
------------------------------------

In order for a website or SPA to access an API hosted under a different
domain name, that API must implement
`Cross-Origin Resource Sharing (CORS) <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>`_.
For a public API, implementing CORS in Falcon can be as simple as passing the
``cors_enable`` flag (set to ``True``) when instantiating
:ref:`your application <app>`.

Further CORS customization is possible via :class:`~falcon.CORSMiddleware`
(for more information on managing CORS in Falcon, see also :ref:`cors`).

For even more sophisticated use cases, have a look at Falcon add-ons from the
community, such as `falcon-cors <https://github.com/lwcolton/falcon-cors>`_, or
try one of the generic
`WSGI CORS libraries available on PyPI <https://pypi.python.org/pypi?%3Aaction=search&term=cors&submit=search>`_.
If you use an API gateway, you might also look into what CORS functionality
it provides at that level.

Why is my request with authorization blocked despite ``cors_enable``?
---------------------------------------------------------------------

When you are making a cross-origin request from the browser (or another HTTP
client verifying CORS policy), and the request is authenticated using the
Authorization header, the browser adds ``authorization`` to
Access-Control-Request-Headers in the preflight (``OPTIONS``) request,
however, the actual authorization credentials are omitted at this stage.

If your request authentication/authorization is performed in a
:ref:`middleware <middleware>` component which rejects requests lacking
authorization credentials by raising an instance of :class:`~.HTTPUnauthorized`
(or rendering a 4XX response in another way), a common pitfall is that even an
``OPTIONS`` request (which is lacking authorization as per the above
explanation) yields an error in this manner. As a result of the failed
preflight, the browser chooses not proceed with the main request.

If you have implemented the authorization middleware yourself, you can simply
let ``OPTIONS`` pass through:

.. code:: python

    class MyAuthMiddleware:
        def process_request(self, req, resp):
            # NOTE: Do not authenticate OPTIONS requests.
            if req.method == 'OPTIONS':
                return

            # -- snip --

            # My authorization logic...

Alternatively, if the middleware comes from a third-party library,
it may be more practical to subclass it:

.. code:: python

    class CORSAwareMiddleware(SomeAuthMiddleware):
        def process_request(self, req, resp):
            # NOTE: Do not authenticate OPTIONS requests.
            if req.method != 'OPTIONS':
                super().process_request(req, resp)

In the case middleware in question instead hooks into ``process_resource()``,
you can use a similar treatment.

If you tried the above, and you still suspect the problem lies within Falcon's
:ref:`CORS middleware <cors>`, it might be a bug! :ref:`Let us know <help>` so
we can help.

How do I implement redirects within Falcon?
-------------------------------------------

Falcon provides a number of exception classes that can be raised to redirect the
client to a different location (see also :ref:`Redirection <redirects>`).

Note, however, that it is more efficient to handle permanent redirects
directly with your web server, if possible, rather than placing additional load
on your app for such requests.

How do I split requests between my original app and the part I migrated to Falcon?
----------------------------------------------------------------------------------

It is common to carve out a portion of an app and reimplement it in
Falcon to boost performance where it is most needed.

If you have access to your load balancer or reverse proxy configuration,
we recommend setting up path or subdomain-based rules to split requests
between your original implementation and the parts that have been
migrated to Falcon (e.g., by adding an additional ``location`` directive
to your NGINX config).

If the above approach isn't an option for your deployment, you can
implement a simple WSGI wrapper that does the same thing:

.. code:: python

    def application(environ, start_response):
        try:
            # NOTE(kgriffs): Prefer the host header; the web server
            # isn't supposed to mess with it, so it should be what
            # the client actually sent.
            host = environ['HTTP_HOST']
        except KeyError:
            # NOTE(kgriffs): According to PEP-3333, this header
            # will always be present.
            host = environ['SERVER_NAME']

        if host.startswith('api.'):
            return falcon_app(environ, start_response)
        elif:
            return webapp2_app(environ, start_response)

See also `PEP 3333 <https://www.python.org/dev/peps/pep-3333/#environ-variables>`_
for a complete list of the variables that are provided via ``environ``.

.. _collection-vs-item-routing:

How do I implement both POSTing and GETing items for the same resource?
-----------------------------------------------------------------------

Suppose you have the following routes::

    # Resource Collection
    GET /resources{?marker, limit}
    POST /resources

    # Resource Item
    GET /resources/{id}
    PATCH /resources/{id}
    DELETE /resources/{id}

You can implement this sort of API by simply using two Python classes, one
to represent a single resource, and another to represent the collection of
said resources. It is common to place both classes in the same module
(see also :ref:`this section of the tutorial <tutorial-serving-images>`.)

Alternatively, you can use suffixed responders to map both routes to the
same resource class:

.. code:: python

    class MyResource:
        def on_get(self, req, resp, id):
            pass

        def on_patch(self, req, resp, id):
            pass

        def on_delete(self, req, resp, id):
            pass

        def on_get_collection(self, req, resp):
            pass

        def on_post_collection(self, req, resp):
            pass


    # -- snip --


    resource = MyResource()
    app.add_route('/resources/{id}', resource)
    app.add_route('/resources', resource, suffix='collection')

.. _recommended-route-layout:

What is the recommended way to map related routes to resource classes?
----------------------------------------------------------------------

Let's say we have the following URL schema::

    GET  /game/ping
    GET  /game/{game_id}
    POST /game/{game_id}
    GET  /game/{game_id}/state
    POST /game/{game_id}/state

We can break this down into three resources::

    Ping:

        GET  /game/ping

    Game:

        GET  /game/{game_id}
        POST /game/{game_id}

    GameState:

        GET  /game/{game_id}/state
        POST /game/{game_id}/state

GameState may be thought of as a sub-resource of Game. It is
a distinct logical entity encapsulated within a more general
Game concept.

In Falcon, these resources would be implemented with standard
classes:

.. code:: python

    class Ping:

        def on_get(self, req, resp):
            resp.text = '{"message": "pong"}'


    class Game:

        def __init__(self, dao):
            self._dao = dao

        def on_get(self, req, resp, game_id):
            pass

        def on_post(self, req, resp, game_id):
            pass


    class GameState:

        def __init__(self, dao):
            self._dao = dao

        def on_get(self, req, resp, game_id):
            pass

        def on_post(self, req, resp, game_id):
            pass


    app = falcon.App()

    # Game and GameState are closely related, and so it
    # probably makes sense for them to share an object
    # in the Data Access Layer. This could just as
    # easily use a DB object or ORM layer.
    #
    # Note how the resources classes provide a layer
    # of abstraction or indirection which makes your
    # app more flexible since the data layer can
    # evolve somewhat independently from the presentation
    # layer.
    game_dao = myapp.DAL.Game(myconfig)

    app.add_route('/game/ping', Ping())
    app.add_route('/game/{game_id}', Game(game_dao))
    app.add_route('/game/{game_id}/state', GameState(game_dao))

Alternatively, a single resource class could implement suffixed responders in
order to handle all three routes:

.. code:: python

    class Game:

        def __init__(self, dao):
            self._dao = dao

        def on_get(self, req, resp, game_id):
            pass

        def on_post(self, req, resp, game_id):
            pass

        def on_get_state(self, req, resp, game_id):
            pass

        def on_post_state(self, req, resp, game_id):
            pass

        def on_get_ping(self, req, resp):
            resp.data = b'{"message": "pong"}'


    # -- snip --


    app = falcon.App()

    game = Game(myapp.DAL.Game(myconfig))

    app.add_route('/game/{game_id}', game)
    app.add_route('/game/{game_id}/state', game, suffix='state')
    app.add_route('/game/ping', game, suffix='ping')

.. _routing_encoded_slashes:

Why is my URL with percent-encoded forward slashes (``%2F``) routed incorrectly?
--------------------------------------------------------------------------------
This is an unfortunate artifact of the WSGI specification, which offers no
standard means of accessing the "raw" request URL. According to PEP 3333,
`the recommended way to reconstruct a request's URL path
<https://www.python.org/dev/peps/pep-3333/#url-reconstruction>`_ is using the
``PATH_INFO`` CGI variable, which is already presented percent-decoded,
effectively making originally percent-encoded forward slashes (``%2F``)
indistinguishable from others passed verbatim (and intended to separate URI
fields).

Although not standardized, some WSGI servers provide the raw URL as a
non-standard extension; for instance, Gunicorn exposes it as ``RAW_URI``,
uWSGI calls it ``REQUEST_URI``, etc. You can implement a WSGI (or ASGI, see the
discussion below) middleware component to overwrite the request path with the
path component of the raw URL, see more in the following recipe:
:ref:`raw_url_path_recipe`.

In contrast to WSGI, the ASGI specification does define a standard connection
HTTP scope variable name (``raw_path``) for the unmodified HTTP path. However,
it is not mandatory, and some applications servers may be unable to provide
it. Nevertheless, we are exploring the possibility of adding an optional
feature to use this raw path for routing in the ASGI flavor of the framework.

Extensibility
~~~~~~~~~~~~~

How do I use WSGI middleware with Falcon?
-----------------------------------------
Instances of :class:`falcon.App` are first-class WSGI apps, so you can use the
standard pattern outlined in PEP-3333. In your main "app" file, you would
simply wrap your api instance with a middleware app. For example:

.. code:: python

    import my_restful_service
    import some_middleware

    app = some_middleware.DoSomethingFancy(my_restful_service.app)

See also the `WSGI middleware example <https://www.python.org/dev/peps/pep-3333/#middleware-components-that-play-both-sides>`_ given in PEP-3333.

How can I pass data from a hook to a responder, and between hooks?
------------------------------------------------------------------
You can inject extra responder kwargs from a hook by adding them
to the *params* dict passed into the hook. You can also set custom attributes
on the :attr:`req.context <falcon.Request.context>` object, as a way of passing
contextual information around:

.. code:: python

    def authorize(req, resp, resource, params):
        # TODO: Check authentication/authorization

        # -- snip --

        req.context.role = 'root'
        req.context.scopes = ('storage', 'things')
        req.context.uid = 0

    # -- snip --

    @falcon.before(authorize)
    def on_post(self, req, resp):
        pass

.. _faq_override_404_500_handlers:

How can I write a custom handler for 404 and 500 pages in falcon?
------------------------------------------------------------------
When a route can not be found for an incoming request, Falcon uses a default
responder that simply raises an instance of :class:`~.HTTPRouteNotFound`, which
the framework will in turn render as a 404 response. You can use
:meth:`falcon.App.add_error_handler` to override the default handler for this
exception type (or for its parent type, :class:`~.HTTPNotFound`).
Alternatively, you may be able to configure your web server to transform the
response for you (e.g., using nginx's ``error_page`` directive).

By default, non-system-exiting exceptions that do not inherit from
:class:`~.HTTPError` or :class:`~.HTTPStatus` are handled by Falcon with a
plain HTTP 500 error. To provide your own 500 logic, you can add a custom error
handler for Python's base :class:`Exception` type. This will not affect the
default handlers for :class:`~.HTTPError` and :class:`~.HTTPStatus`.

See :ref:`errors` and the :meth:`falcon.App.add_error_handler` docs for more
details.

Request Handling
~~~~~~~~~~~~~~~~

How do I authenticate requests?
-------------------------------
Hooks and middleware components can be used together to authenticate and
authorize requests. For example, a middleware component could be used to
parse incoming credentials and place the results in
:attr:`req.context <falcon.Request.context>`.
Downstream components or hooks could then use this information to
authorize the request, taking into account the user's role and the requested
resource.

Why does req.stream.read() hang for certain requests?
-----------------------------------------------------

This behavior is an unfortunate artifact of the request body mechanics not
being fully defined by the WSGI spec (PEP-3333). This is discussed in the
reference documentation for :attr:`~falcon.Request.stream`, and a workaround
is provided in the form of :attr:`~falcon.Request.bounded_stream`.

.. _trailing_slash_in_path:

How does Falcon handle a trailing slash in the request path?
------------------------------------------------------------
If your app sets :attr:`~falcon.RequestOptions.strip_url_path_trailing_slash` to
``True``, Falcon will normalize incoming URI paths to simplify later processing
and improve the predictability of application logic. This can be helpful when
implementing a REST API schema that does not interpret a
trailing slash character as referring to the name of an implicit sub-resource,
as traditionally used by websites to reference index pages.

For example, with this option enabled, adding a route for ``'/foo/bar'``
implicitly adds a route for ``'/foo/bar/'``. In other words, requests coming
in for either path will be sent to the same resource.

.. warning::

    If :attr:`~falcon.RequestOptions.strip_url_path_trailing_slash` is enabled,
    adding a route with a trailing slash will effectively make it unreachable
    from normal routing (theoretically, it may still be matched by rewriting
    the request path in middleware).

    In this case, routes should be added without a trailing slash (obviously
    except the root path ``'/'``), such as ``'/foo/bar'`` in the example above.

.. note::

    Starting with version 2.0, the default for the
    :attr:`~falcon.RequestOptions.strip_url_path_trailing_slash` request option
    changed from ``True`` to ``False``.

Why is my query parameter missing from the req object?
------------------------------------------------------
If a query param does not have a value and the
:attr:`~falcon.RequestOptions.keep_blank_qs_values` request option is set to
``False`` (the default as of Falcon 2.0+ is ``True``), Falcon will ignore that
parameter.
For example, passing ``'foo'`` or ``'foo='`` will result in the parameter being
ignored.

If you would like to recognize such parameters, the
:attr:`~falcon.RequestOptions.keep_blank_qs_values` request option should be
set to ``True`` (or simply kept at its default value in Falcon 2.0+). Request
options are set globally for each instance of :class:`falcon.App` via the
:attr:`~falcon.App.req_options` property. For example:

.. code:: python

    app.req_options.keep_blank_qs_values = True

Why are '+' characters in my params being converted to spaces?
--------------------------------------------------------------
The ``+`` character is often used instead of ``%20`` to represent spaces in
query string params, due to the historical conflation of form parameter encoding
(``application/x-www-form-urlencoded``) and URI percent-encoding.  Therefore,
Falcon, converts ``+`` to a space when decoding strings.

To work around this, RFC 3986 specifies ``+`` as a reserved character,
and recommends percent-encoding any such characters when their literal value is
desired (``%2B`` in the case of ``+``).

.. _access_urlencoded_form:

How can I access POSTed form params?
------------------------------------
By default, Falcon does not consume request bodies. However, a :ref:`media
handler <media>` for the ``application/x-www-form-urlencoded`` content type is
installed by default, thus making the POSTed form available as
:attr:`Request.media <falcon.Request.media>` with zero configuration:

.. code:: python

    import falcon


    class MyResource:
        def on_post(self, req, resp):
            # TODO: Handle the submitted URL-encoded form
            form = req.media

            # NOTE: Falcon chooses the right media handler automatically, but
            #   if we wanted to differentiate from, for instance, JSON, we
            #   could check whether req.content_type == falcon.MEDIA_URLENCODED
            #   or use mimeparse to implement more sophisticated logic.

.. note::
   In prior versions of Falcon, a POSTed URL-encoded form could be automatically
   consumed and merged into :attr:`~falcon.Request.params` by setting the
   :attr:`~falcon.RequestOptions.auto_parse_form_urlencoded` option to ``True``. This
   behavior is still supported in the Falcon 3.x series. However, it has been
   deprecated in favor of :class:`~.media.URLEncodedFormHandler`, and the
   option to merge URL-encoded form data into
   :attr:`~falcon.Request.params` may be removed in a future release.

POSTed form parameters may also be read directly from
:attr:`~falcon.Request.stream` and parsed via
:meth:`falcon.uri.parse_query_string` or :func:`urllib.parse.parse_qs`.

.. _access_multipart_files:

How can I access POSTed files?
------------------------------

If files are ``POST``\ed as part of a :ref:`multipart form <multipart>`, the
default :class:`MultipartFormHandler <falcon.media.MultipartFormHandler>` can
be used to efficiently parse the submitted ``multipart/form-data``
:ref:`request media <media>` by iterating over the multipart
:class:`body parts <falcon.media.multipart.BodyPart>`:

.. code:: python

    for part in req.media:
        # TODO: Do something with the body part
        pass

.. _multipart_cloud_upload:

How can I save POSTed files (from a multipart form) directly to AWS S3?
-----------------------------------------------------------------------

As highlighted in the previous answer dealing with
:ref:`files posted as multipart form <access_multipart_files>`,
:class:`falcon.media.MultipartFormHandler` may be used to iterate over the
uploaded multipart body parts.

The `stream` of a body part is a file-like object implementing the ``read()``
method, making it compatible with ``boto3``\'s
`upload_fileobj <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.upload_fileobj>`_:

.. tab-set::

    .. tab-item:: WSGI
        :sync: wsgi

        .. code:: python

            import boto3

            # -- snip --

            s3 = boto3.client('s3')

            for part in req.media:
                if part.name == 'myfile':
                    s3.upload_fileobj(part.stream, 'mybucket', 'mykey')

    .. tab-item:: ASGI
        :sync: asgi

        .. code:: python

            import aioboto3

            # -- snip --

            session = aioboto3.Session()

            form = await req.get_media()
            async for part in form:
                if part.name == 'myfile':
                    async with session.client('s3') as s3:
                        await s3.upload_fileobj(part.stream, 'mybucket', 'mykey')

        .. note::
            The ASGI snippet requires the
            `aioboto3 <https://pypi.org/project/aioboto3/>`__ async wrapper in
            lieu of ``boto3`` (as the latter only offers a synchronous
            interface at the time of writing).

.. note::
   Falcon is not endorsing any particular cloud service provider, and AWS S3
   and ``boto3`` are referenced here just as a popular example. The same
   pattern can be applied to any storage API that supports streaming directly
   from a file-like object.

How do I parse a nested multipart form?
---------------------------------------
Falcon does not offer official support for parsing nested multipart forms
(i.e., where multiple files for a single field are transmitted using a nested
``multipart/mixed`` part) at this time. The usage is considered deprecated
according to the `living HTML5 standard
<https://html.spec.whatwg.org/multipage/form-control-infrastructure.html>`_ and
`RFC 7578, Section 4.3 <https://tools.ietf.org/html/rfc7578#section-4.3>`_.

.. tip::
    If your app absolutely must deal with such legacy forms, the parser may
    actually be capable of the task. See more in this recipe:
    :ref:`nested-multipart-forms`.

How do I retrieve a JSON value from the query string?
-----------------------------------------------------
To retrieve a JSON-encoded value from the query string, Falcon provides the
:meth:`~falcon.Request.get_param_as_json` method, an example of which is given
below:

.. code:: python

    import falcon


    class LocationResource:

        def on_get(self, req, resp):
            places = {
                'Chandigarh, India': {
                    'lat': 30.692781,
                    'long': 76.740875
                },

                'Ontario, Canada': {
                    'lat': 43.539814,
                    'long': -80.246094
                }
            }

            coordinates = req.get_param_as_json('place')

            place = None
            for (key, value) in places.items():
                if coordinates == value:
                    place = key
                    break

            resp.media = {
                'place': place
            }


    app = falcon.App()
    app.add_route('/locations', LocationResource())

In the example above, ``LocationResource`` expects a query string containing
a JSON-encoded value named ``'place'``. This value can be fetched and
decoded from JSON in a single step with the
:meth:`~falcon.Request.get_param_as_json` method. Given a request URL
such as:

    ``/locations?place={"lat":43.539814,"long":-80.246094}``

The `coordinates` variable will be set to a :class:`dict` as expected.

By default, the :attr:`~falcon.RequestOptions.auto_parse_qs_csv` option is
set to ``False``. The example above assumes this default.

On the other hand, when :attr:`~falcon.RequestOptions.auto_parse_qs_csv` is set
to ``True``, Falcon treats commas in a query string as literal characters
delimiting a comma-separated list. For example, given the query string
``?c=1,2,3``, Falcon will add this to your ``request.params``
dictionary as ``{'c': ['1', '2', '3']}``. If you attempt to use JSON in the
value of the query string, for example ``?c={"a":1,"b":2}``, the value will be
added to ``request.params`` in an unexpected way: ``{'c': ['{"a":1', '"b":2}']}``.

Commas are a reserved character that can be escaped according to
`RFC 3986 - 2.2. Reserved Characters <https://tools.ietf.org/html/rfc3986#section-2.2>`_,
so one possible solution is to percent encode any commas that appear in your
JSON query string.

The other option is to leave
:attr:`~falcon.RequestOptions.auto_parse_qs_csv` disabled and simply use JSON
array syntax in lieu of CSV.

When :attr:`~falcon.RequestOptions.auto_parse_qs_csv` is not enabled, the
value of the query string ``?c={"a":1,"b":2}`` will be added to
the ``req.params`` dictionary as ``{'c': '{"a":1,"b":2}'}``.
This lets you consume JSON whether or not the client chooses to percent-encode
commas in the request. In this case, you can retrieve the raw JSON string
via :meth:`~falcon.Request.get_param`, or use the
:meth:`~falcon.Request.get_param_as_json` convenience method as
demonstrated above.

How can I handle forward slashes within a route template field?
---------------------------------------------------------------

Falcon 4 shipped initial support for
`field converters <http://falcon.readthedocs.io/en/stable/api/routing.html#field-converters>`_
that can match multiple segments. The ``path`` :class:`field converter <~falcon.routing.PathConverter>`
is capable of consuming multiple path segments when placed at the end of the URL template.

In previous versions, you can work around the issue by implementing a Falcon
middleware component to rewrite the path before it is routed. If you control
the clients, you can percent-encode forward slashes inside the field in
question, however, note that pre-processing is unavoidable in order to access
the raw encoded URI too. See also: :ref:`routing_encoded_slashes`

.. _bare_class_context_type:

How do I adapt my code to default context type changes in Falcon 2.0?
---------------------------------------------------------------------

The default request/response context type has been changed from dict to a bare
class in Falcon 2.0. Instead of setting dictionary items, you can now simply
set attributes on the object:

.. code:: python

   # Before Falcon 2.0
   req.context['cache_backend'] = MyUltraFastCache.connect()

   # Falcon 2.0
   req.context.cache_backend = MyUltraFastCache.connect()

The new default context type emulates a dict-like mapping interface in a way
that context attributes are linked to dict items, i.e. setting an object
attribute also sets the corresponding dict item, and vice versa. As a result,
existing code will largely work unmodified with Falcon 2.0. Nevertheless, it is
recommended to migrate to the new interface as outlined above since the
dict-like mapping interface may be removed from the context type in a future
release.

.. warning::
   If you need to mix-and-match both approaches under migration, beware that
   setting attributes such as *items* or *values* would obviously shadow the
   corresponding mapping interface functions.

If an existing project is making extensive use of dictionary contexts, the type
can be explicitly overridden back to dict by employing custom request/response
types:

.. code:: python

    class RequestWithDictContext(falcon.Request):
        context_type = dict

    class ResponseWithDictContext(falcon.Response):
        context_type = dict

    # -- snip --

    app = falcon.App(request_type=RequestWithDictContext,
                     response_type=ResponseWithDictContext)

Response Handling
~~~~~~~~~~~~~~~~~

When would I use media, data, text, and stream?
-----------------------------------------------

These four attributes are mutually exclusive, you should only set one when
defining your response.

:attr:`resp.media <falcon.Response.media>` is used when you want to use the
Falcon serialization mechanism. Just assign data to the attribute and Falcon
will take care of the rest.

.. code:: python

    class MyResource:
        def on_get(self, req, resp):
            resp.media = {'hello': 'World'}

:attr:`resp.text <falcon.Response.text>` and
:attr:`resp.data <falcon.Response.data>` are very similar, they both allow you
to set the body of the response. The difference being,
:attr:`~falcon.Response.text` takes a string, and :attr:`~falcon.Response.data`
takes bytes.

.. code:: python

    class MyResource:
        def on_get(self, req, resp):
            resp.text = json.dumps({'hello': 'World'})

        def on_post(self, req, resp):
            resp.data = b'{"hello": "World"}'

:attr:`resp.stream <falcon.Response.stream>` allows you to set a generator that
yields bytes, or a file-like object with a ``read()`` method that returns
bytes. In the case of a file-like object, the framework will call ``read()``
until the stream is exhausted.

.. code:: python

    class MyResource:
        def on_get(self, req, resp):
            resp.stream = open('myfile.json', mode='rb')

See also the :ref:`outputting_csv_recipe` recipe for an example of using
:attr:`resp.stream <falcon.Response.stream>` with a generator.

How can I use resp.media with types like datetime?
--------------------------------------------------

The default JSON handler for :attr:`resp.media <falcon.Response.media>` only
supports the objects and types listed in the table documented under
:any:`json.JSONEncoder`.

To handle additional types in JSON, you can either serialize them beforehand,
or create a custom JSON media handler that sets the `default` param for
:func:`json.dumps`. When deserializing an incoming request body, you may also
wish to implement `object_hook` for :func:`json.loads`. Note, however, that
setting the `default` or `object_hook` params can negatively impact the
performance of (de)serialization.

If you use an alternative JSON library, you might also look whether it provides
support for additional data types. For instance, the popular ``orjson`` opts to
automatically serialize :mod:`dataclasses`, :mod:`enums <enum>`,
:class:`~datetime.datetime` objects, etc.

Furthermore, different Internet media types such as YAML,
:class:`msgpack <falcon.media.MessagePackHandler>`, etc might support more data
types than JSON, either as part of the respective (de)serialization format, or
via custom type extensions.

.. seealso:: See :ref:`custom-media-json-encoder` for an example on how to
    use a custom json encoder.

.. note:: When testing an application employing a custom JSON encoder, bear in
    mind that :class:`~.testing.TestClient` is decoupled from the app, and it
    simulates requests as if they were performed by a third-party client (just
    sans network). Therefore, passing the **json** parameter to
    :ref:`simulate_* <testing_standalone_methods>` methods will effectively
    use the stdlib's :func:`json.dumps`. If you want to serialize custom
    objects for testing, you will need to dump them into a string yourself, and
    pass it using the **body** parameter instead (accompanied by the
    ``application/json`` content type header).

Does Falcon set Content-Length or do I need to do that explicitly?
------------------------------------------------------------------
Falcon will try to do this for you, based on the value of
:attr:`resp.text <falcon.Response.text>`,
:attr:`resp.data <falcon.Response.data>` or
:attr:`resp.media <falcon.Response.media>` (whichever is set in the response,
checked in that order).

For dynamically-generated content, you can choose to not set
:attr:`~falcon.Response.content_length`, in which case Falcon will then leave
off the Content-Length header, and hopefully your WSGI server will do the
Right Thing™ (assuming you've told the server to enable keep-alive, it may
choose to use chunked encoding).

.. note:: PEP-3333 prohibits apps from setting hop-by-hop headers itself,
    such as Transfer-Encoding.

Similar to WSGI, the `ASGI HTTP connection scope
<https://asgi.readthedocs.io/en/latest/specs/www.html#http-connection-scope>`_
specification states that responses without Content-Length "may be chunked as
the server sees fit".

Why is an empty response body returned when I raise an instance of HTTPError?
-----------------------------------------------------------------------------

Falcon attempts to serialize the :class:`~falcon.HTTPError` instance using its
:meth:`~falcon.HTTPError.to_json` or :meth:`~falcon.HTTPError.to_xml` methods,
according to the Accept header in the request. If neither JSON nor XML is
acceptable, no response body will be generated. You can override this behavior
if needed via :meth:`~falcon.App.set_error_serializer`.

I'm setting a response body, but it isn't getting returned. What's going on?
----------------------------------------------------------------------------
Falcon skips processing the response body when, according to the HTTP
spec, no body should be returned. If the client
sends a HEAD request, the framework will always return an empty body.
Falcon will also return an empty body whenever the response status is any
of the following::

    falcon.HTTP_100
    falcon.HTTP_204
    falcon.HTTP_416
    falcon.HTTP_304

If you have another case where the body isn't being returned, it's probably a
bug! :ref:`Let us know <help>` so we can help.

I'm setting a cookie, but it isn't being returned in subsequent requests.
-------------------------------------------------------------------------
By default, Falcon enables the `secure` cookie attribute. Therefore, if you are
testing your app over HTTP (instead of HTTPS), the client will not send the
cookie in subsequent requests.

(See also the :ref:`cookie documentation <cookie-secure-attribute>`.)

.. _serve-downloadable-as:

How can I serve a downloadable file with Falcon?
------------------------------------------------
In the ``on_get()`` responder method for the resource, you can tell the user
agent to download the file by setting the Content-Disposition header. Falcon
includes the :attr:`~falcon.Response.downloadable_as` property to make this
easy:

.. code:: python

    resp.downloadable_as = 'report.pdf'

See also the :ref:`outputting_csv_recipe` recipe for a more involved example of
dynamically generated downloadable content.

.. _faq_header_names_lowercase:

Why is Falcon changing my header names to lowercase?
----------------------------------------------------

Falcon always lowercases header names before storing them in the internal
:class:`Response <falcon.Response>` structures in order to make the response
header handling straightforward and performant, as header name lookup can be
done using a simple ``dict``. Since HTTP headers are case insensitive, this
optimization should normally not affect your API consumers.

In the unlikely case you absolutely must deal with non-conformant HTTP clients
expecting a specific header name capitalization, see this recipe how to
override header names using generic WSGI middleware:
:ref:`capitalizing_response_headers`.

Note that this question only applies to the WSGI flavor of Falcon. The
`ASGI HTTP scope specification
<https://asgi.readthedocs.io/en/latest/specs/www.html#response-start-send-event>`_
requires HTTP header names to be lowercased.

Furthermore, the HTTP2 standard also mandates that header field names MUST be
converted to lowercase (see `RFC 7540, Section 8.1.2
<https://httpwg.org/specs/rfc7540.html#rfc.section.8.1.2>`_).

.. _faq_static_files:

Can Falcon serve static files?
------------------------------

Falcon makes it easy to efficiently serve static files by simply assigning an
open file to ``resp.stream`` :ref:`as demonstrated in the tutorial
<tutorial-serving-images>`. You can also serve an entire directory of files via
:meth:`falcon.App.add_static_route`. However, if possible, it is best to serve
static files directly from a web server like Nginx, or from a CDN.

Misc.
~~~~~

How do I manage my database connections?
----------------------------------------

Assuming your database library manages its own connection pool, all you need
to do is initialize the client and pass an instance of it into your resource
classes. For example, using SQLAlchemy Core:

.. code:: python

    engine = create_engine('sqlite:///:memory:')
    resource = SomeResource(engine)

Then, within ``SomeResource``:

.. code:: python

    # Read from the DB
    with self._engine.connect() as connection:
        result = connection.execute(some_table.select())
    for row in result:
        # TODO: Do something with each row

    result.close()

    # -- snip --

    # Write to the DB within a transaction
    with self._engine.begin() as connection:
        r1 = connection.execute(some_table.select())

        # -- snip --

        connection.execute(
            some_table.insert(),
            col1=7,
            col2='this is some data'
        )

When using a data access layer, simply pass the engine into your data
access objects instead. See also
`this sample Falcon project <https://github.com/jmvrbanac/falcon-example>`_
that demonstrates using an ORM with Falcon.

You can also create a middleware component to automatically check out
database connections for each request, but this can make it harder to track
down errors, or to tune for the needs of individual requests.

If you need to transparently handle reconnecting after an error, or for other
use cases that may not be supported by your client library, simply encapsulate
the client library within a management class that handles all the tricky bits,
and pass that around instead.

If you are interested in the middleware approach, the
`falcon-sqla <https://github.com/vytas7/falcon-sqla>`__ library can be used to
automatically check out and close SQLAlchemy connections that way (although it
also supports the explicit context manager pattern).

How do I manage my database connections with ASGI?
--------------------------------------------------

This example is similar to the above one, but it uses ASGI lifecycle hooks
to set up a connection pool, and to dispose it at the end of the application.
The example uses `psycopg <https://www.psycopg.org/psycopg3/docs/api/index.html>`_
to connect to a PostgreSQL database, but a similar pattern may be adapted to
other asynchronous database libraries.

.. code:: python

    import psycopg_pool

    url = 'postgresql://scott:tiger@127.0.0.1:5432/test'

    class AsyncPoolMiddleware:
        def __init__(self):
            self._pool = None

        async def process_startup(self, scope, event):
            self._pool = psycopg_pool.AsyncConnectionPool(url)
            await self._pool.wait()  # created the pooled connections

        async def process_shutdown(self, scope, event):
            if self._pool:
                await self._pool.close()

        async def process_request(self, req, resp):
            req.context.pool = self._pool

            try:
                req.context.conn = await self._pool.getconn()
            except Exception:
                req.context.conn = None
                raise

        async def process_response(self, req, resp, resource, req_succeeded):
            if req.context.conn:
                await self._pool.putconn(req.context.conn)

Then, an example resource may use the connection or the pool:

.. code:: python

    class Numbers:
        async def on_get(self, req, resp):
            # This endpoint uses the connection created for the request by the Middleware
            async with req.context.conn.cursor() as cur:
                await cur.execute('SELECT value FROM numbers')
                rows = await cur.fetchall()

            resp.media = [row[0] for row in rows]

        async def on_get_with_pool(self, req, resp):
            # This endpoint uses the pool to acquire a connection
            async with req.context.pool.connection() as conn:
                cur = await conn.execute('SELECT value FROM numbers')
                rows = await cur.fetchall()
                await cur.close()

            resp.media = [row[0] for row in rows]

The application can then be used as

.. code:: python

    from falcon.asgi import App

    app = App(middleware=[AsyncPoolMiddleware()])
    num = Numbers()
    app.add_route('/conn', num)
    app.add_route('/pool', num, suffix='with_pool')

.. _configuration-approaches:

What is the recommended approach for app configuration?
-------------------------------------------------------

When it comes to app configuration, Falcon is not opinionated. You are free to
choose from any of the excellent general-purpose configuration libraries
maintained by the Python community. It’s pretty much up to you if you want to
use the standard library or something like ``aumbry`` as demonstrated by this
`Falcon example app <https://github.com/jmvrbanac/falcon-example/tree/master/example>`_.

(See also the **Configuration** section of our
`Complementary Packages wiki page <https://github.com/falconry/falcon/wiki/Complementary-Packages>`_.
You may also wish to search PyPI for other options).

After choosing a configuration library, the only remaining question is how to
access configuration options throughout your app.

People usually fall into two camps when it comes to this question. The first
camp likes to instantiate a config object and pass that around to the
initializers of the resource classes so the data sharing is explicit. The second
camp likes to create a config module and import that wherever it’s needed.

With the latter approach, to control when the config is actually loaded,
it’s best not to instantiate it at
the top level of the config module’s namespace. This avoids any problematic
side-effects that may be caused by loading the config whenever Python happens
to process the first import of the config module. Instead,
consider implementing a function in the module that returns a new or cached
config object on demand.

How do I test my Falcon app? Can I use pytest?
----------------------------------------------

Falcon's testing framework supports both ``unittest`` and ``pytest``. In fact,
the tutorial in the docs provides an excellent introduction to
`testing Falcon apps with pytest <http://falcon.readthedocs.io/en/stable/user/tutorial.html#testing-your-application>`_.

(See also: `Testing <http://falcon.readthedocs.io/en/stable/api/testing.html>`_)

Can I shut my server down cleanly from the app?
-----------------------------------------------

Normally, the lifetime of an app server is controlled by other means than from
inside the running app, and there is no standardized way for a WSGI or ASGI
framework to shut down the server programmatically.

However, if you need to spin up a real server for testing purposes (such as for
collecting coverage while interacting with other services over the network),
your app server of choice may offer a Python API or hooks that you can
integrate into your app.

For instance, the stdlib's :mod:`wsgiref` server inherits from
:class:`~socketserver.TCPServer`, which can be stopped by calling its
``shutdown()`` method. Just make sure to perform the call from a different
thread (otherwise it may deadlock):

.. code:: python

    import http
    import threading
    import wsgiref.simple_server

    import falcon


    class Shutdown:
        def __init__(self, httpd):
            self._httpd = httpd

        def on_post(self, req, resp):
            thread = threading.Thread(target=self._httpd.shutdown, daemon=True)
            thread.start()

            resp.content_type = falcon.MEDIA_TEXT
            resp.text = 'Shutting down...\n'
            resp.status = http.HTTPStatus.ACCEPTED


    with wsgiref.simple_server.make_server('', 8000, app := falcon.App()) as httpd:
        app.add_route('/shutdown', Shutdown(httpd))
        print('Serving on port 8000, POST to /shutdown to stop...')
        httpd.serve_forever()

.. warning::
   While ``wsgiref.simple_server`` is handy for integration testing, it builds
   upon :mod:`http.server`, which is not recommended for production. (See
   :ref:`install` on how to install a production-ready WSGI or ASGI server.)

How can I set cookies when simulating requests?
-----------------------------------------------

The easiest way is to simply pass the ``cookies`` parameter into
``simulate_request``. Here is an example:

.. code:: python

    import falcon
    import falcon.testing
    import pytest

    class TastyCookies:

        def on_get(self, req, resp):
            resp.media = {'cookies': req.cookies}


    @pytest.fixture
    def client():
        app = falcon.App()
        app.add_route('/cookies', TastyCookies())

        return falcon.testing.TestClient(app)


    def test_cookies(client):
        resp = client.simulate_get('/cookies', cookies={'cookie': 'cookie value'})

        assert resp.json == {'cookies': {'cookie': 'cookie value'}}


Alternatively, you can set the Cookie header directly as demonstrated in this version of ``test_cookies()``

.. code:: python

    def test_cookies(client):
        resp = client.simulate_get('/cookies', headers={'Cookie': 'xxx=yyy'})

        assert resp.json == {'cookies': {'xxx': 'yyy'}}

To include multiple values, simply use ``"; "`` to separate each name-value
pair. For example, if you were to pass ``{'Cookie': 'xxx=yyy; hello=world'}``,
you would get ``{'cookies': {'xxx': 'yyy', 'hello': 'world'}}``.
