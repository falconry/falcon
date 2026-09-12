.. _app:

The App Class
=============

Falcon supports both the WSGI (:class:`falcon.App`) and
ASGI (:class:`falcon.asgi.App`) protocols. This is done
by instantiating the respective ``App`` class to create a
callable WSGI or ASGI "application".

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
