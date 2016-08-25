.. _routing:

Routing
=======

The *falcon.routing* module contains utilities used internally by
:py:meth:`falcon.API` to route requests. They are exposed here for use by
custom routing engines.

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

        def find(self, uri):
            """Search for a route that matches the given URI.

            Args:
                uri (str): Request URI to match to a route.

            Returns:
                tuple: A 3-member tuple composed of (resource, method_map, params)
                    or ``None`` if no route is found.
            """

A custom routing engine may be specified when instantiating
:py:meth:`falcon.API`. For example:

.. code:: python

    fancy = FancyRouter()
    api = API(router=fancy)

.. automodule:: falcon.routing
    :members: create_http_method_map, compile_uri_template, CompiledRouter
