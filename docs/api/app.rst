.. _app:

The App Class
=============

Falcon supports both the WSGI (:class:`falcon.App`) and
ASGI (:class:`falcon.asgi.App`) protocols. This is done
by instantiating the respective ``App`` class to create a
callable WSGI or ASGI "application".

.. image:: /_static/img/diagrams/falcon-app-parts.svg
    :alt: The falcon.App builds req and resp for each request and calls every part
        in turn. Built into Falcon: the router, which matches the path to a URI
        template and picks your resource; media handlers, which parse req.media
        and render resp.media; and error handlers, which turn exceptions into
        HTTP error responses. Written by you: middleware, whose process_request
        and process_response run for every request; hooks, @falcon.before and
        @falcon.after, which wrap one resource or responder; and responders such
        as on_get(req, resp) on your resource class.

Because Falcon's ``App`` classes are built on
`WSGI <https://www.python.org/dev/peps/pep-3333/>`_ and
`ASGI <https://asgi.readthedocs.io/en/latest/>`_,
you can host them with any standard-compliant server.

.. code:: python

    import falcon
    import falcon.asgi

    wsgi_app = falcon.App()
    asgi_app = falcon.asgi.App()

WSGI App
--------

.. autoclass:: falcon.App
    :members:

ASGI App
--------

.. autoclass:: falcon.asgi.App
    :members:

Options
-------

.. autoclass:: falcon.RequestOptions
    :members:

.. autoclass:: falcon.ResponseOptions
    :members:

.. _compiled_router_options:
.. autoclass:: falcon.routing.CompiledRouterOptions
    :members:
