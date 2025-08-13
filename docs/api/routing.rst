.. _routing:

Routing
=======

Falcon uses resource-based routing to encourage a RESTful architectural style.
Each resource is represented by a class that is responsible for handling all of
the HTTP methods that the resource supports.

For each HTTP method supported by the resource, the class implements a
corresponding Python method with a name that starts with ``on_`` and ends in the
lowercased HTTP method name (e.g., ``on_get()``, ``on_patch()``,
``on_delete()``, etc.)

.. note::
    Resources in Falcon are represented by a single class instance that is
    created at application startup when the routes are configured. This
    minimizes routing overhead and simplifies the implementation of resource
    classes. In the case of WSGI apps, this also means that resource classes
    must be implemented in a thread-safe manner (see also:
    :ref:`faq_thread_safety`).

Falcon routes incoming requests (including :ref:`WebSocket handshakes <ws>`) to
resources based on a set of URI templates. If the path requested by the client
matches the template for a given route, the request is then passed on to the
associated resource for processing.

Here's a quick example to show how all the pieces fit together:

.. tab-set::

    .. tab-item:: WSGI

        .. code:: python

            import json

            import falcon


            class ImagesResource:

                def on_get(self, req, resp):
                    doc = {
                        'images': [
                            {
                                'href': '/images/1eaf6ef1-7f2d-4ecc-a8d5-6e8adba7cc0e.png'
                            }
                        ]
                    }

                    # Create a JSON representation of the resource; this could
                    #   also be done automatically by assigning to resp.media
                    resp.text = json.dumps(doc, ensure_ascii=False)

                    # The following line can be omitted because 200 is the default
                    # status returned by the framework, but it is included here to
                    # illustrate how this may be overridden as needed.
                    resp.status = falcon.HTTP_200


            app = falcon.App()

            images = ImagesResource()
            app.add_route('/images', images)

    .. tab-item:: ASGI

        .. code:: python

            import json

            import falcon
            import falcon.asgi


            class ImagesResource:

                async def on_get(self, req, resp):
                    doc = {
                        'images': [
                            {
                                'href': '/images/1eaf6ef1-7f2d-4ecc-a8d5-6e8adba7cc0e.png'
                            }
                        ]
                    }

                    # Create a JSON representation of the resource; this could
                    #   also be done automatically by assigning to resp.media
                    resp.text = json.dumps(doc, ensure_ascii=False)

                    # The following line can be omitted because 200 is the default
                    # status returned by the framework, but it is included here to
                    # illustrate how this may be overridden as needed.
                    resp.status = falcon.HTTP_200


            app = falcon.asgi.App()

            images = ImagesResource()
            app.add_route('/images', images)

If no route matches the request, control then passes to a default responder that
simply raises an instance of :class:`~.HTTPRouteNotFound`. By default, this
error will be rendered as a 404 response for a regular HTTP request, and a 403
response with a 3404 close code for a :ref:`WebSocket <ws>` handshake. This
behavior can be modified by adding a custom error handler (see also
:ref:`this FAQ topic <faq_override_404_500_handlers>`).

On the other hand, if a route is matched but the resource does not implement a
responder for the requested HTTP method, the framework invokes a default
responder that raises an instance of :class:`~.HTTPMethodNotAllowed`. This class
will be rendered by default as a 405 response for a regular HTTP request, and a
403 response with a 3405 close code for a :ref:`WebSocket <ws>` handshake.

Falcon also provides a default responder for OPTIONS requests that takes into
account which methods are implemented for the target resource.

Default Behavior
----------------

Falcon's default routing engine is based on a decision tree that is
first compiled into Python code, and then evaluated by the runtime.
By default, the decision tree is compiled only when the router handles
the first request. See :class:`.CompiledRouter` for more details.

The :meth:`falcon.App.add_route` and :meth:`falcon.asgi.App.add_route` methods
are used to associate a URI template with a resource. Falcon then maps incoming
requests to resources based on these templates.

Falcon's default router uses Python classes to represent resources. In
practice, these classes act as controllers in your application. They
convert an incoming request into one or more internal actions, and then
compose a response back to the client based on the results of those
actions. (See also:
:ref:`Tutorial: Creating Resources <tutorial_resources>`)

.. code:: none

               ┌────────────┐
    request  → │            │
               │ Resource   │ ↻ Orchestrate the requested action
               │ Controller │ ↻ Compose the result
    response ← │            │
               └────────────┘

Each resource class defines various "responder" methods, one for each
HTTP method the resource allows. Responder names start with ``on_`` and
are named according to which HTTP method they handle, as in ``on_get()``,
``on_post()``, ``on_put()``, etc.

.. note::
    If your resource does not support a particular
    HTTP method, simply omit the corresponding responder and
    Falcon will use a default responder that raises
    an instance of :class:`~.HTTPMethodNotAllowed` when that
    method is requested. Normally this results in sending a
    405 response back to the client.

Responders must always define at least two arguments to receive
:class:`~.falcon.Request` and :class:`~.falcon.Response` objects, respectively::

    def on_post(self, req, resp):
        pass

For ASGI apps, the responder must be a coroutine function::

    async def on_post(self, req, resp):
        pass

The :class:`~.falcon.Request` object represents the incoming HTTP
request. It exposes properties and methods for examining headers,
query string parameters, and other metadata associated with
the request. A file-like stream object is also provided for reading
any data that was included in the body of the request.

The :class:`~.falcon.Response` object represents the application's
HTTP response to the above request. It provides properties
and methods for setting status, header and body data. The
:class:`~.falcon.Response` object also exposes a dict-like
:attr:`~.falcon.Response.context` property for passing arbitrary
data to hooks and middleware methods.

.. note::
    Rather than directly manipulate the :class:`~.falcon.Response`
    object, a responder may raise an instance of either
    :class:`~.HTTPError` or :class:`~.HTTPStatus`. Falcon will
    convert these exceptions to appropriate HTTP responses.
    Alternatively, you can handle them yourself via
    :meth:`~.falcon.App.add_error_handler`.

In addition to the standard `req` and `resp` parameters, if the
route's template contains field expressions, any responder that
desires to receive requests for that route must accept arguments
named after the respective field names defined in the template.

A field expression consists of a bracketed field name. For
example, given the following template::

    /user/{name}

A PUT request to ``'/user/kgriffs'`` would cause the framework to invoke
the ``on_put()`` responder method on the route's resource class, passing
``'kgriffs'`` via an additional `name` argument defined by the responder:

.. tab-set::

    .. tab-item:: WSGI

        .. code:: python

            # Template fields correspond to named arguments or keyword
            #   arguments, following the usual req and resp args.
            def on_put(self, req, resp, name):
                pass

    .. tab-item:: ASGI

        .. code:: python

            # Template fields correspond to named arguments or keyword
            #   arguments, following the usual req and resp args.
            async def on_put(self, req, resp, name):
                pass

Because field names correspond to argument names in responder
methods, they must be valid Python identifiers.

Individual path segments may contain one or more field
expressions, and fields need not span the entire path
segment. For example::

    /repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}
    /serviceRoot/People('{name}')

(See also the :ref:`Falcon tutorial <tutorial>` for additional examples
and a walkthrough of setting up routes within the context of a sample
application.)

.. _routing_field_converters:

Field Converters
----------------

Falcon's default router supports the use of field converters to
transform a URI template field value. Field converters may also perform
simple input validation. For example, the following URI template uses
the `int` converter to convert the value of `tid` to a Python ``int``,
but only if it has exactly eight digits::

    /teams/{tid:int(8)}

If the value is malformed and can not be converted, Falcon will reject
the request with a 404 response to the client.

Converters are instantiated with the argument specification given in the
field expression. These specifications follow the standard Python syntax
for passing arguments. For example, the comments in the following code
show how a converter would be instantiated given different argument
specifications in the URI template:

.. code:: python

    # IntConverter()
    app.add_route(
        '/a/{some_field:int}',
        some_resource
    )

    # IntConverter(8)
    app.add_route(
        '/b/{some_field:int(8)}',
        some_resource
    )

    # IntConverter(8, min=10000000)
    app.add_route(
        '/c/{some_field:int(8, min=10000000)}',
        some_resource
    )

(See also how :class:`~.UUIDConverter` is used in Falcon's ASGI tutorial:
:ref:`asgi_tutorial_image_resources`.)

.. _routing_builtin_converters:

Built-in Converters
-------------------

============  =================================  ==================================================================
 Identifier    Class                              Example
============  =================================  ==================================================================
 ``int``       :class:`~.IntConverter`            ``/teams/{tid:int(8)}``
 ``uuid``      :class:`~.UUIDConverter`           ``/diff/{left:uuid}...{right:uuid}``
 ``dt``        :class:`~.DateTimeConverter`       ``/logs/{day:dt("%Y-%m-%d")}``
 ``float``     :class:`~.FloatConverter`          ``/python/versions/{version:float(min=3.7)}``
 ``path``      :class:`~.PathConverter`           ``/prefix/{other:path}``
============  =================================  ==================================================================

|

.. autoclass:: falcon.routing.IntConverter
    :members:

.. autoclass:: falcon.routing.FloatConverter
    :members:

.. autoclass:: falcon.routing.UUIDConverter
    :members:

.. autoclass:: falcon.routing.DateTimeConverter
    :members:

.. autoclass:: falcon.routing.PathConverter
    :members:

.. _routing_custom_converters:

Custom Converters
-----------------

Custom converters can be registered via the
:attr:`~.CompiledRouterOptions.converters` router option. A converter is
simply a class that implements the ``BaseConverter`` interface:

.. autoclass:: falcon.routing.BaseConverter
    :members:

.. _routing_custom:

Custom Routers
--------------

A custom routing engine may be specified when instantiating
:meth:`falcon.App` or :meth:`falcon.asgi.App`. For example:

.. code:: python

    router = MyRouter()
    app = App(router=router)

Custom routers may derive from the default :class:`~.CompiledRouter`
engine, or implement a completely different routing strategy (such as
object-based routing).

A custom router is any class that implements the following interface:

.. code:: python

    class MyRouter:
        def add_route(self, uri_template, resource, **kwargs):
            """Adds a route between URI path template and resource.

            Args:
                uri_template (str): A URI template to use for the route
                resource (object): The resource instance to associate with
                    the URI template.

            Keyword Args:
                suffix (str): Optional responder name suffix for this
                    route. If a suffix is provided, Falcon will map GET
                    requests to ``on_get_{suffix}()``, POST requests to
                    ``on_post_{suffix}()``, etc. In this way, multiple
                    closely-related routes can be mapped to the same
                    resource. For example, a single resource class can
                    use suffixed responders to distinguish requests for
                    a single item vs. a collection of those same items.
                    Another class might use a suffixed responder to handle
                    a shortlink route in addition to the regular route for
                    the resource.

                **kwargs (dict): Accepts any additional keyword arguments
                    that were originally passed to the falcon.App.add_route()
                    method. These arguments MUST be accepted via the
                    double-star variadic pattern (**kwargs), and ignore any
                    unrecognized or unsupported arguments.
            """

        def find(self, uri, req=None):
            """Search for a route that matches the given partial URI.

            Args:
                uri(str): The requested path to route.

            Keyword Args:
                 req(Request): The Request object that will be passed to
                    the routed responder. The router may use `req` to
                    further differentiate the requested route. For
                    example, a header may be used to determine the
                    desired API version and route the request
                    accordingly.

                    Note:
                        The `req` keyword argument was added in version
                        1.2. To ensure backwards-compatibility, routers
                        that do not implement this argument are still
                        supported.

            Returns:
                tuple: A 4-member tuple composed of (resource, method_map,
                    params, uri_template), or ``None`` if no route matches
                    the requested path.

            """

Suffixed Responders
-------------------

While Falcon encourages the REST architectural style, it is flexible enough to accommodate other
paradigms. Consider the task of building an API for a calculator which can both add and subtract
two numbers. You could implement the
following:

.. code:: python

    class Add():
        def on_get(self, req, resp):
            resp.text = str(req.get_param_as_int('x') + req.get_param_as_int('y'))
            resp.status = falcon.HTTP_200


    class Subtract():
        def on_get(self, req, resp):
            resp.text = str(req.get_param_as_int('x') - req.get_param_as_int('y'))
            resp.status = falcon.HTTP_200


    add = Add()
    subtract = Subtract()
    app = falcon.App()
    app.add_route('/add', add)
    app.add_route('/subtract', subtract)

However, this approach highlights a situation in which grouping by resource may not make sense for
your domain. In this context, adding and subtracting don't seem to conceptually map to two separate resource
collections. Instead of separating them based on the idea of "getting" different resources from
each, we might want to group them based on the attributes of their function (i.e., take two
numbers, do something to them, return the result).

With Suffixed Responders, we can do just that, rewriting the example above in a more procedural
style:

.. code:: python

    class Calculator():
        def on_get_add(self, req, resp):
            resp.text = str(req.get_param_as_int('x') + req.get_param_as_int('y'))
            resp.status = falcon.HTTP_200

        def on_get_subtract(self, req, resp):
            resp.text = str(req.get_param_as_int('x') - req.get_param_as_int('y'))
            resp.status = falcon.HTTP_200


    calc = Calculator()
    app = falcon.App()
    app.add_route('/add', calc, suffix='add')
    app.add_route('/subtract', calc, suffix='subtract')

In the second iteration, using Suffixed Responders, we're able to group responders based on their
actions rather than the data they represent. This gives us added flexibility to accommodate
situations in which a purely RESTful approach simply doesn't fit.

Default Router
--------------

.. autoclass:: falcon.routing.CompiledRouter
    :members:


Routing Utilities
-----------------

The *falcon.routing* module contains the following utilities that may
be used by custom routing engines.

.. autofunction:: falcon.routing.map_http_methods

.. autofunction:: falcon.routing.set_default_responders

.. autofunction:: falcon.app_helpers.prepare_middleware

.. autofunction:: falcon.app_helpers.prepare_middleware_ws


Static File Routes
------------------

Falcon can serve static files directly from a WSGI or ASGI application
using the below sink-like :class:`~falcon.routing.StaticRoute`.

Instances of :class:`~falcon.routing.StaticRoute` are normally created via
:meth:`falcon.App.add_static_route`
(please see, however, the documentation of :meth:`~falcon.App.add_static_route`
for the performance implications of serving files through a Python app).

.. autoclass:: falcon.routing.StaticRoute
    :members:


Custom HTTP Methods
-------------------

While not normally advised, some applications may need to support non-standard
HTTP methods, in addition to the standard HTTP methods like GET and PUT. To
support custom HTTP methods, use one of the following methods:

- Ideally, if you don't use hooks in your application, you can easily add the
  custom methods in your application setup by overriding the value of
  ``falcon.constants.COMBINED_METHODS``. For example::

    import falcon.constants
    falcon.constants.COMBINED_METHODS += ['FOO', 'BAR']

- Due to the nature of hooks, if you do use them, you'll need to define the
  FALCON_CUSTOM_HTTP_METHODS environment variable as a comma-delimited list
  of custom methods. For example::

    $ export FALCON_CUSTOM_HTTP_METHODS=FOO,BAR


Once you have used the appropriate method, your custom methods should be active.
You then can define request methods like any other HTTP method:

.. tab-set::

    .. tab-item:: WSGI

        .. code:: python

            # Handle the custom FOO method
            def on_foo(self, req, resp):
                pass

    .. tab-item:: ASGI

        .. code:: python

            # Handle the custom FOO method
            async def on_foo(self, req, resp):
                pass
