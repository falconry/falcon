.. _request_asgi:

ASGI Request & Response
=======================

Instances of the :class:`falcon.asgi.Request` and
:class:`falcon.asgi.Response` classes are passed into responders as
the second and third arguments, respectively:

.. code:: python

    import falcon.asgi


    class Resource:

        async def on_get(self, req, resp):
            resp.media = {'message': 'Hello world!'}
            resp.status = 200


    # -- snip --


    app = falcon.asgi.App()
    app.add_route('/', Resource())

Request
-------

.. autoclass:: falcon.asgi.Request
    :members:
    :inherited-members:
    :exclude-members: media, context_type

.. autoclass:: falcon.asgi.BoundedStream
    :members:

Response
--------

.. autoclass:: falcon.asgi.Response
    :members:
    :inherited-members:
    :exclude-members: context_type, add_link

.. autoclass:: falcon.asgi.SSEvent
    :members:
