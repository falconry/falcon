.. _cors:

CORS
=====

`Cross Origin Resource Sharing <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>`_
(CORS) is an additional security check performed by modern
browsers to prevent unauthorized requests between different domains.

When implementing
a web API, it is common to have to also implement a CORS policy. Therefore,
Falcon provides an easy way to enable a simple CORS policy via a flag passed
to :any:`falcon.App`.

By default, Falcon's built-in CORS support is disabled, so that any cross-origin
requests will be blocked by the browser. Passing ``cors_enabled=True`` will
cause the framework to include the necessary response headers to allow access
from any origin to any route in the app. Individual responders may override this
behavior by setting the Access-Control-Allow-Origin header explicitly.

Whether or not you implement a CORS policy, we recommend also putting a robust
AuthN/Z layer in place to authorize individual clients, as needed, to protect
sensitive resources.

Usage
-----

.. code:: python

    import falcon

    # Enable a simple CORS policy for all responses
    app = falcon.App(cors_enable=True)

