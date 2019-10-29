.. _api:

The App Class
=============

Falcon's App class is a WSGI "application" that you can host with any
standard-compliant WSGI server.

.. code:: python

    import falcon

    app = falcon.App()

.. autoclass:: falcon.App
    :members:

.. autoclass:: falcon.RequestOptions
    :members:

.. autoclass:: falcon.ResponseOptions
    :members:

.. _compiled_router_options:
.. autoclass:: falcon.routing.CompiledRouterOptions
    :noindex:
