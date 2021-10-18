.. _cors:

CORS
=====

`Cross Origin Resource Sharing <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>`_
(CORS) is an additional security check performed by modern
browsers to prevent unauthorized requests between different domains.

When developing a web API, it is common to also implement a CORS
policy. Therefore, Falcon provides an easy way to enable a simple CORS policy
via a flag passed to :class:`falcon.App` or :class:`falcon.asgi.App`.

By default, Falcon's built-in CORS support is disabled, so that any cross-origin
requests will be blocked by the browser. Passing ``cors_enable=True`` will
cause the framework to include the necessary response headers to allow access
from any origin to any route in the app. Individual responders may override this
behavior by setting the ``Access-Control-Allow-Origin`` header explicitly.

Whether or not you implement a CORS policy, we recommend also putting a robust
AuthN/Z layer in place to authorize individual clients, as needed, to protect
sensitive resources.

Directly passing the :class:`falcon.CORSMiddleware` middleware to the application
allows customization of the CORS policy applied. The middleware allows customizing
the allowed origins, if credentials should be allowed and if additional headers
can be exposed.

Usage
-----

.. tabs::

    .. tab:: WSGI

        .. code:: python

            import falcon

            # Enable a simple CORS policy for all responses
            app = falcon.App(cors_enable=True)

            # Alternatively, enable CORS policy for example.com and allow
            # credentials
            app = falcon.App(middleware=falcon.CORSMiddleware(
                allow_origins='example.com', allow_credentials='*'))

    .. tab:: ASGI

        .. code:: python

            import falcon.asgi

            # Enable a simple CORS policy for all responses
            app = falcon.asgi.App(cors_enable=True)

            # Alternatively, Enable CORS policy for example.com and allow
            # credentials
            app = falcon.asgi.App(middleware=falcon.CORSMiddleware(
                allow_origins='example.com', allow_credentials='*'))

.. note::
    Passing the ``cors_enable`` parameter set to ``True`` should be seen as
    mutually exclusive with directly passing an instance of
    :class:`~falcon.CORSMiddleware` to the application's initializer.

CORSMiddleware
--------------

.. autoclass:: falcon.CORSMiddleware
