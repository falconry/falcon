.. _routing:

Routing
=======

Falcon routes incoming requests to resources based on a set of URI
templates. If the path requested by the client matches the template for
a given route, the request is then passed on to the associated resource
for processing.

If no route matches the request, control then passes to a default
responder that simply raises an instance of :class:`~.HTTPNotFound`.
Normally this will result in sending a 404 response back to the
client.

Here's a quick example to show how all the pieces fit together:

.. code:: python

    import json

    import falcon

    class ImagesResource(object):

        def on_get(self, req, resp):
            doc = {
                'images': [
                    {
                        'href': '/images/1eaf6ef1-7f2d-4ecc-a8d5-6e8adba7cc0e.png'
                    }
                ]
            }

            # Create a JSON representation of the resource
            resp.body = json.dumps(doc, ensure_ascii=False)

            # The following line can be omitted because 200 is the default
            # status returned by the framework, but it is included here to
            # illustrate how this may be overridden as needed.
            resp.status = falcon.HTTP_200

    api = application = falcon.API()

    images = ImagesResource()
    api.add_route('/images', images)


Default Router
--------------

Falcon's default routing engine is based on a decision tree that is
first compiled into Python code, and then evaluated by the runtime.

The :meth:`~.API.add_route` method is used to associate a URI template
with a resource. Falcon then maps incoming requests to resources
based on these templates.

Falcon's default router uses Python classes to represent resources. In
practice, these classes act as controllers in your application. They
convert an incoming request into one or more internal actions, and then
compose a response back to the client based on the results of those
actions. (See also:
:ref:`Tutorial: Creating Resources <tutorial_resources>`)

.. code::

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
:class:`~.Request` and :class:`~.Response` objects, respectively::

    def on_post(self, req, resp):
        pass

The :class:`~.Request` object represents the incoming HTTP
request. It exposes properties and methods for examining headers,
query string parameters, and other metadata associated with
the request. A file-like stream object is also provided for reading
any data that was included in the body of the request.

The :class:`~.Response` object represents the application's
HTTP response to the above request. It provides properties
and methods for setting status, header and body data. The
:class:`~.Response` object also exposes a dict-like
:attr:`~.Response.context` property for passing arbitrary
data to hooks and middleware methods.

.. note::
    Rather than directly manipulate the :class:`~.Response`
    object, a responder may raise an instance of either
    :class:`~.HTTPError` or :class:`~.HTTPStatus`. Falcon will
    convert these exceptions to appropriate HTTP responses.
    Alternatively, you can handle them youself via
    :meth:`~.API.add_error_handler`.

In addition to the standard `req` and `resp` parameters, if the
route's template contains field expressions, any responder that
desires to receive requests for that route must accept arguments
named after the respective field names defined in the template.

A field expression consists of a bracketed field name. For
example, given the following template::

    /user/{name}

A PUT request to "/user/kgriffs" would be routed to:

.. code:: python

    def on_put(self, req, resp, name):
        pass

Because field names correspond to argument names in responder
methods, they must be valid Python identifiers.

Individual path segments may contain one or more field
expressions, and fields need not span the entire path
segment. For example::

    /repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}
    /serviceRoot/People('{name}')

(See also the :ref:`Falcon tutorial <tutorial>` for additional examples
and a walkthough of setting up routes within the context of a sample
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
    api.add_route(
        '/a/{some_field:int}',
        some_resource
    )

    # IntConverter(8)
    api.add_route(
        '/b/{some_field:int(8)}',
        some_resource
    )

    # IntConverter(8, min=10000000)
    api.add_route(
        '/c/{some_field:int(8, min=10000000)}',
        some_resource
    )

Built-in Converters
-------------------

============  =================================  ==================================================================
 Identifier    Class                              Example
============  =================================  ==================================================================
 ``int``       :class:`~.IntConverter`            ``/teams/{tid:int(8)}``
 ``uuid``      :class:`~.UUIDConverter`           ``/diff/{left:uuid}...{right:uuid}``
 ``dt``        :class:`~.DateTimeConverter`       ``/logs/{day:dt("%Y-%m-%d")}``
============  =================================  ==================================================================

|

.. autoclass:: falcon.routing.IntConverter
    :members:

.. autoclass:: falcon.routing.UUIDConverter
    :members:

.. autoclass:: falcon.routing.DateTimeConverter
    :members:

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
:py:meth:`falcon.API`. For example:

.. code:: python

    router = MyRouter()
    api = API(router=router)

Custom routers may derive from the default :py:class:`~.CompiledRouter`
engine, or implement a completely different routing strategy (such as
object-based routing).

A custom router is any class that implements the following interface:

.. code:: python

    class MyRouter(object):
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
                    that were originally passed to the falcon.API.add_route()
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

.. autofunction:: falcon.routing.compile_uri_template
