.. _cors:

Cors
=====

Cross Origin Resource Sharing is an additional security check done by moderns
browsers to avoid request between different domains. To allow it falcon
has easy way to enable or disable your CORS policies at the initialization
of a :any:`falcon.API`. By default CORS policies are enable in your :any:`falcon.API`
object, so if any request is coming from a different domain will be blocked
by the browser as default because falcon will not send the headers required
by the browser to allow ross site resource sharing. You can change this easy
just by instantiating a :any:`falcon.API` passing the parameter `cors_enable`
as True


Usage
-----

.. code:: python

    import falcon

    # falcon.API instances are callable WSGI apps
    app = falcon.API(cors_enable=True)

