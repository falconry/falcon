.. _faq:

FAQ
===

.. contents:: :local:

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

Why does raising an error inside a resource crash my app?
---------------------------------------------------------
Generally speaking, Falcon assumes that resource responders (such as
``on_get()``, ``on_post()``, etc.) will, for the most part, do the right thing.
In other words, Falcon doesn't try very hard to protect responder code from
itself.

This approach reduces the number of checks that Falcon
would otherwise have to perform, making the framework more efficient. With
that in mind, writing a high-quality API based on Falcon requires that:

#. Resource responders set response variables to sane values.
#. Your code is well-tested, with high code coverage.
#. Errors are anticipated, detected, and handled appropriately within
   each responder and with the aid of custom error handlers.

.. tip:: Falcon will re-raise errors that do not inherit from
    :class:`~falcon.HTTPError` unless you have registered a custom error
    handler for that type (see also: :ref:`falcon.API <api>`).

How do I generate API documentation for my Falcon API?
------------------------------------------------------
When it comes to API documentation, some developers prefer to use the API
implementation as the user contract or source of truth (taking an
implementation-first approach), while other developers prefer to use the API
spec itself as the contract, implementing and testing the API against that spec
(taking a design-first approach).

At the risk of erring on the side of flexiblity, Falcon does not provide API
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

That being said, IO-bound Falcon APIs are usually scaled via multiple
processes and green threads (courtesy of the `gevent <http://www.gevent.org/>`_
library or similar) which aren't truly running concurrently, so there may be
some edge cases where Falcon is not thread-safe that we aren't aware of. If you
run into any issues, please let us know.

Does Falcon support asyncio?
------------------------------

Due to the limitations of WSGI, Falcon is unable to support ``asyncio`` at this
time. However, we are exploring alternatives to WSGI (such
as `ASGI <https://github.com/django/asgiref/blob/master/specs/asgi.rst>`_)
that will allow us to support asyncio natively in the future.

In the meantime, we recommend using the battle-tested
`gevent <http://www.gevent.org/>`_ library via
Gunicorn or uWSGI to scale IO-bound services.
`meinheld <https://pypi.org/project/meinheld/>`_ has also been used
successfully by the community to power high-throughput, low-latency services.
Note that if you use Gunicorn, you can combine gevent and PyPy to achieve an
impressive level of performance. (Unfortunately, uWSGI does not yet support
using gevent and PyPy together.)

Does Falcon support WebSocket?
------------------------------

Due to the limitations of WSGI, Falcon is unable to support the WebSocket
protocol as stated above.

In the meantime, you might try leveraging
`uWSGI's native WebSocket support <http://uwsgi.readthedocs.io/en/latest/WebSockets.html>`_,
or implementing a standalone service via Aymeric Augustin's
handy `websockets <https://pypi.python.org/pypi/websockets/4.0.1>`_ library.

Routing
~~~~~~~

How do I implement CORS with Falcon?
------------------------------------

In order for a website or SPA to access an API hosted under a different
domain name, that API must implement
`Cross-Origin Resource Sharing (CORS) <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>`_.
For a public API, implementing CORS in Falcon can be as simple as implementing
a middleware component similar to the following:

.. code:: python

    class CORSComponent(object):
        def process_response(self, req, resp, resource, req_succeeded):
            resp.set_header('Access-Control-Allow-Origin', '*')

            if (req_succeeded
                and req.method == 'OPTIONS'
                and req.get_header('Access-Control-Request-Method')
            ):
                # NOTE(kgriffs): This is a CORS preflight request. Patch the
                #   response accordingly.

                allow = resp.get_header('Allow')
                resp.delete_header('Allow')

                allow_headers = req.get_header(
                    'Access-Control-Request-Headers',
                    default='*'
                )

                resp.set_headers((
                    ('Access-Control-Allow-Methods', allow),
                    ('Access-Control-Allow-Headers', allow_headers),
                    ('Access-Control-Max-Age', '86400'),  # 24 hours
                ))

When using the above approach, OPTIONS requests must also be special-cased in
any other middleware or hooks you use for auth, content-negotiation, etc. For
example, you will typically skip auth for preflight requests because it is
simply unnecessary; note that such request do not include the Authorization
header in any case.

For more sophisticated use cases, have a look at Falcon add-ons from the
community, such as `falcon-cors <https://github.com/lwcolton/falcon-cors>`_, or
try one of the generic
`WSGI CORS libraries available on PyPI <https://pypi.python.org/pypi?%3Aaction=search&term=cors&submit=search>`_.
If you use an API gateway, you might also look into what CORS functionaly
it provides at that level.

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
            return falcon_app(environ, startswith)
        elif:
            return webapp2_app(environ, startswith)

See also `PEP 3333 <https://www.python.org/dev/peps/pep-3333/#environ-variables>`_
for a complete list of the variables that are provided via ``environ``.

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

    class MyResource(object):
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


    # ...


    resource = MyResource()
    api.add_route('/resources/{id}', resource)
    api.add_route('/resources', resource, suffix='collection')

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

    class Ping(object):

        def on_get(self, req, resp):
            resp.body = '{"message": "pong"}'


    class Game(object):

        def __init__(self, dao):
            self._dao = dao

        def on_get(self, req, resp, game_id):
            pass

        def on_post(self, req, resp, game_id):
            pass


    class GameState(object):

        def __init__(self, dao):
            self._dao = dao

        def on_get(self, req, resp, game_id):
            pass

        def on_post(self, req, resp, game_id):
            pass


    api = falcon.API()

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

    api.add_route('/game/ping', Ping())
    api.add_route('/game/{game_id}', Game(game_dao))
    api.add_route('/game/{game_id}/state', GameState(game_dao))

Alternatively, a single resource class could implement suffixed responders in
order to handle all three routes:

.. code:: python

    class Game(object):

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


    # ...


    api = falcon.API()

    game = Game(myapp.DAL.Game(myconfig))

    api.add_route('/game/{game_id}', game)
    api.add_route('/game/{game_id}/state', game, suffix='state')
    api.add_route('/game/ping', game, suffix='ping')

Extensibility
~~~~~~~~~~~~~

How do I use WSGI middleware with Falcon?
-----------------------------------------
Instances of :class:`falcon.API` are first-class WSGI apps, so you can use the
standard pattern outlined in PEP-3333. In your main "app" file, you would
simply wrap your api instance with a middleware app. For example:

.. code:: python

    import my_restful_service
    import some_middleware

    app = some_middleware.DoSomethingFancy(my_restful_service.api)

See also the `WSGI middleware example <https://www.python.org/dev/peps/pep-3333/#middleware-components-that-play-both-sides>`_ given in PEP-3333.

How can I pass data from a hook to a responder, and between hooks?
------------------------------------------------------------------
You can inject extra responder kwargs from a hook by adding them
to the *params* dict passed into the hook. You can also add custom data to
the ``req.context`` dict, as a way of passing contextual information around.

How can I write a custom handler for 404 and 500 pages in falcon?
------------------------------------------------------------------
When a route can not be found for an incoming request, Falcon uses a default
responder that simply raises an instance of :attr:`falcon.HTTPNotFound`. You
can use :meth:`falcon.API.add_error_handler` to register a custom error handler
for this exception type. Alternatively, you may be able to configure your web
server to transform the response for you (e.g., using Nginx's ``error_page``
directive).

500 errors are typically the result of an unhandled exception making its way
up to the web server. To handle these errors more gracefully, you can add a
custom error handler for Python's base :class:`Exception` type.

Request Handling
~~~~~~~~~~~~~~~~

How do I authenticate requests?
-------------------------------
Hooks and middleware components can be used together to authenticate and
authorize requests. For example, a middleware component could be used to
parse incoming credentials and place the results in ``req.context``.
Downstream components or hooks could then use this information to
authorize the request, taking into account the user's role and the requested
resource.

Why does req.stream.read() hang for certain requests?
-----------------------------------------------------

This behavior is an unfortunate artifact of the request body mechanics not
being fully defined by the WSGI spec (PEP-3333). This is discussed in the
reference documentation for :attr:`~falcon.Request.stream`, and a workaround
is provided in the form of :attr:`~falcon.Request.bounded_stream`.

Why are trailing slashes trimmed from req.path?
-----------------------------------------------
By default, Falcon normalizes incoming URI paths to simplify later processing
and improve the predictability of application logic. This behavior can be
disabled via the :attr:`~falcon.RequestOptions.strip_url_path_trailing_slash`
request option.

Note also that routing is also normalized, so adding a route for "/foo/bar"
also implicitly adds a route for "/foo/bar/". Requests coming in for either
path will be sent to the same resource.

Why is my query parameter missing from the req object?
------------------------------------------------------
If a query param does not have a value, Falcon will by default ignore that
parameter. For example, passing ``'foo'`` or ``'foo='`` will result in the
parameter being ignored.

If you would like to recognize such parameters, you must set the
`keep_blank_qs_values` request option to ``True``. Request options are set
globally for each instance of :class:`falcon.API` via the
:attr:`~falcon.API.req_options` property. For example:

.. code:: python

    api.req_options.keep_blank_qs_values = True

Why are '+' characters in my params being converted to spaces?
--------------------------------------------------------------
The ``+`` character is often used instead of ``%20`` to represent spaces in
query string params, due to the historical conflation of form parameter encoding
(``application/x-www-form-urlencoded``) and URI percent-encoding.  Therefore,
Falcon, converts ``+`` to a space when decoding strings.

To work around this, RFC 3986 specifies ``+`` as a reserved character,
and recommends percent-encoding any such characters when their literal value is
desired (``%2B`` in the case of ``+``).

How can I access POSTed form params?
------------------------------------
By default, Falcon does not consume request bodies. However, setting
the :attr:`~RequestOptions.auto_parse_form_urlencoded` to ``True``
on an instance of ``falcon.API``
will cause the framework to consume the request body when the
content type is ``application/x-www-form-urlencoded``, making
the form parameters accessible via :attr:`~.Request.params`,
:meth:`~.Request.get_param`, etc.

.. code:: python

    api.req_options.auto_parse_form_urlencoded = True

Alternatively, POSTed form parameters may be read directly from
:attr:`~.Request.stream` and parsed via
:meth:`falcon.uri.parse_query_string` or
`urllib.parse.parse_qs() <https://docs.python.org/3.6/library/urllib.parse.html#urllib.parse.parse_qs>`_.

How can I access POSTed files?
------------------------------
Falcon does not currently support parsing files submitted by
an HTTP form (``multipart/form-data``), although we do plan
to add this feature in a future version. In the meantime,
you can use the standard ``cgi.FieldStorage`` class to
parse the request:

.. code:: python

    # TODO: Either validate that content type is multipart/form-data
    # here, or in another hook before allowing execution to proceed.

    # This must be done to avoid a bug in cgi.FieldStorage
    env = req.env
    env.setdefault('QUERY_STRING', '')

    # TODO: Add error handling, when the request is not formatted
    # correctly or does not contain the desired field...

    # TODO: Consider overriding make_file, so that you can
    # stream directly to the destination rather than
    # buffering using TemporaryFile (see http://goo.gl/Yo8h3P)
    form = cgi.FieldStorage(fp=req.stream, environ=env)

    file_item = form[name]
    if file_item.file:
        # TODO: It's an uploaded file... read it in
    else:
        # TODO: Raise an error

You might also try this
`streaming_form_data <https://streaming-form-data.readthedocs.io/en/latest/>`_
package by Siddhant Goel, or searching PyPI for additional options from the
community.

How do I consume a query string that has a JSON value?
------------------------------------------------------
Falcon defaults to treating commas in a query string as literal characters
delimiting a comma separated list. For example, given
the query string ``?c=1,2,3``, Falcon defaults to adding this to your
``request.params`` dictionary as ``{'c': ['1', '2', '3']}``. If you attempt
to use JSON in the value of the query string, for example ``?c={'a':1,'b':2}``,
the value will get added to your ``request.params`` in a way that you probably
don't expect: ``{'c': ["{'a':1", "'b':2}"]}``.

Commas are a reserved character that can be escaped according to
`RFC 3986 - 2.2. Reserved Characters <https://tools.ietf.org/html/rfc3986#section-2.2>`_,
so one possible solution is to percent encode any commas that appear in your
JSON query string. The other option is to switch the way Falcon
handles commas in a query string by setting the
:attr:`~falcon.RequestOptions.auto_parse_qs_csv` to ``False`` on an instance of
:class:`falcon.API`:

.. code:: python

    api.auto_parse_qs_csv = False

When :attr:`~falcon.RequestOptions.auto_parse_qs_csv` is set to ``False``, the
value of the query string ``?c={'a':1,'b':2}`` will be added to
the ``req.params`` dictionary as  ``{'c': "{'a':1,'b':2}"}``.
This lets you consume JSON whether or not the client chooses to escape
commas in the request.

How can I handle forward slashes within a route template field?
---------------------------------------------------------------

In Falcon 1.3 we shipped initial support for
`field converters <http://falcon.readthedocs.io/en/stable/api/routing.html#field-converters>`_.
We’ve discussed building on this feature to support consuming multiple path
segments ala Flask. This work is currently planned for 2.0.

In the meantime, the workaround is to percent-encode the forward slash. If you
don’t control the clients and can't enforce this, you can implement a Falcon
middleware component to rewrite the path before it is routed.

Response Handling
~~~~~~~~~~~~~~~~~

How can I use resp.media with types like datetime?
--------------------------------------------------

The default JSON handler for ``resp.media`` only supports the objects and types
listed in the table documented under
`json.JSONEncoder <https://docs.python.org/3.6/library/json.html#json.JSONEncoder>`_.
To handle additional types, you can either serialize them beforehand, or create
a custom JSON media handler that sets the `default` param for ``json.dumps()``.
When deserializing an incoming request body, you may also wish to implement
`object_hook` for ``json.loads()``. Note, however, that setting the `default` or
`object_hook` params can negatively impact the performance of (de)serialization.

Does Falcon set Content-Length or do I need to do that explicitly?
------------------------------------------------------------------
Falcon will try to do this for you, based on the value of ``resp.body``,
``resp.data``, or ``resp.stream_len`` (whichever is set in the response,
checked in that order.)

For dynamically-generated content, you can choose to not set ``stream_len``,
in which case Falcon will then leave off the Content-Length header, and
hopefully your WSGI server will do the Right Thing™ (assuming you've told
it to enable keep-alive).

.. note:: PEP-3333 prohibits apps from setting hop-by-hop headers itself,
    such as Transfer-Encoding.

Why is an empty response body returned when I raise an instance of HTTPError?
-----------------------------------------------------------------------------

Falcon attempts to serialize the :class:`~falcon.HTTPError` instance using its
:meth:`~falcon.HTTPError.to_json` or :meth:`~falcon.HTTPError.to_xml` methods,
according to the Accept header in the request. If neither JSON nor XML is
acceptable, no response body will be generated. You can override this behavior
if needed via :meth:`~falcon.API.set_error_serializer`.

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

How can I serve a downloadable file with falcon?
------------------------------------------------
In the ``on_get()`` responder method for the resource, you can tell the user
agent to download the file by setting the Content-Disposition header. Falcon
includes the :attr:`~falcon.Request.downloadable_as` property to make this
easy:

.. code:: python

    resp.downloadable_as = 'report.pdf'

Can Falcon serve static files?
------------------------------

Falcon makes it easy to efficiently serve static files by simply assigning an
open file to ``resp.stream`` :ref:`as demonstrated in the tutorial
<tutorial-serving-images>`. You can also serve an entire directory of files via
:meth:`falcon.API.add_static_route`. However, if possible, it is best to serve
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
    result = self._engine.execute(some_table.select())
    for row in result:
        # ....
    result.close()

    # ...

    # Write to the DB within a transaction
    with self._engine.begin() as connection:
        r1 = connection.execute(some_table.select())
        # ...
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

What is the recommended approach for making configuration variables available to multiple resource classes?
-----------------------------------------------------------------------------------------------------------

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

Other than that, it’s pretty much up to you if you want to use the standard
library config library or something like ``aumbry`` as demonstrated by this
`falcon example app <https://github.com/jmvrbanac/falcon-example/tree/master/example>`_

(See also the **Configuration** section of our
`Complementary Packages wiki page <https://github.com/falconry/falcon/wiki/Complementary-Packages>`_.
You may also wish to search PyPI for other options).

How do I test my Falcon app? Can I use pytest?
----------------------------------------------

Falcon's testing framework supports both ``unittest`` and ``pytest``. In fact,
the tutorial in the docs provides an excellent introduction to
`testing Falcon apps with pytest <http://falcon.readthedocs.io/en/stable/user/tutorial.html#testing-your-application>`_.

(See also: `Testing <http://falcon.readthedocs.io/en/stable/api/testing.html>`_)
