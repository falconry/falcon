.. _request:

WSGI Request & Response
=======================

Instances of the :class:`falcon.Request` and
:class:`falcon.Response` classes are passed into WSGI app responders as the
second and third arguments, respectively:

.. code:: python

    import falcon


    class Resource:

        def on_get(self, req, resp):
            resp.media = {'message': 'Hello world!'}
            resp.status = falcon.HTTP_200


    # -- snip --


    app = falcon.App()
    app.add_route('/', Resource())


Request
-------

.. autoclass:: falcon.Request
    :members:
    :exclude-members: media, context_type


.. autoclass:: falcon.Forwarded
    :members:

.. autoclass:: falcon.stream.BoundedStream
    :members:

Response
--------

.. autoclass:: falcon.Response
    :members:
    :exclude-members: context_type, add_link
