.. _request:

Req/Resp
========

Instances of the Request and Response classes are passed into responders as the second
and third arguments, respectively.

.. code:: python

    import falcon


    class Resource(object):

        def on_get(self, req, resp):
            resp.body = '{"message": "Hello world!"}'
            resp.status = falcon.HTTP_200

Request
-------

.. autoclass:: falcon.Request
    :members:

Response
--------

.. autoclass:: falcon.Response
    :members:



