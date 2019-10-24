.. _cors:

CORS
=====

`Cross Origin Resource Sharing <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>`_ 
(CORS) is an additional security check performed by modern
browsers to prevent unauthorized requests between different domains. When implementing
a web API, it is common to have to also implement a CORS policy. Therefore, Falcon
provides an easy way to enable a simple CORS policy via a flag passed 
to :any:`falcon.API`. By default, Falcon's built-in CORS support is disabled,
so that any cross-origin requests will be blocked
by the browser. Passing ``cors_enabled=True`` will cause the framework to include
the necessary response headers to allow access from
any origin to any route in the app. 

When it comes to APIs, we recommend using this 
feature only when a robust AuthN/Z layer is also in place to authorize individual 
clients, as needed, to protect sensitive resources.

Usage
-----

.. code:: python

    import falcon

    # falcon.API instances are callable WSGI apps
    app = falcon.API(cors_enable=True)

