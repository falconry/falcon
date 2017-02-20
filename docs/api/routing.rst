.. _routing:

Routing
=======

The *falcon.routing* module contains utilities used internally by
:py:meth:`falcon.API` to route requests. They are exposed here for use by
custom routing engines.

Custom routers may derive from the default :py:class:`~.CompiledRouter`
engine, or implement a completely different routing strategy (such as
object-based routing).

A custom router is any class that implements the following interface:

.. code:: python

    class FancyRouter(object):
        def add_route(self, uri_template, method_map, resource):
            """Adds a route between URI path template and resource.

            Args:
                uri_template (str): The URI template to add.
                method_map (dict): A method map obtained by calling
                    falcon.routing.create_http_method_map.
                resource (object): Instance of the resource class that
                    will handle requests for the given URI.
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

A custom routing engine may be specified when instantiating
:py:meth:`falcon.API`. For example:

.. code:: python

    fancy = FancyRouter()
    api = API(router=fancy)

.. automodule:: falcon.routing
    :members: create_http_method_map, compile_uri_template, CompiledRouter
