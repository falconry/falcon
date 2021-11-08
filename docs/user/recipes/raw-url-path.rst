.. _raw_url_path_recipe:

Decoding Raw URL Path
=====================

This recipe demonstrates how to access the "raw" request path using
non-standard (WSGI) or optional (ASGI) application server extensions.
This is useful when, for instance, a URI field has been percent-encoded in
order to distinguish between forward slashes inside the field's value, and
slashes used to separate fields. See also: :ref:`routing_encoded_slashes`

WSGI
----

In the WSGI flavor of the framework, :attr:`req.path <falcon.Request.path>` is
based on the ``PATH_INFO`` CGI variable, which is already presented
percent-decoded. Some application servers expose the raw URL under another,
non-standard, CGI variable name. Let us implement a middleware component that
understands two such extensions, ``RAW_URI`` (Gunicorn, Werkzeug's dev server)
and ``REQUEST_URI`` (uWSGI, Waitress, Werkzeug's dev server), and replaces
``req.path`` with a value extracted from the raw URL:

.. code:: python

    import falcon


    class RawPathComponent:
        def process_request(self, req, resp):
            raw_uri = req.env.get('RAW_URI', req.env.get('REQUEST_URI'))

            # NOTE: Reconstruct the percent-encoded path from the raw URI.
            if raw_uri:
                req.path, _, _ = raw_uri.partition('?')


    class PathResource:
        def on_get(self, req, resp, path):
            # NOTE: path here is potentially percent-encoded.
            path = falcon.uri.decode(path)

            resp.media = {'path': path}


    app = falcon.App(middleware=[RawPathComponent()])
    app.add_route('/example/{path}', PathResource())

Running the above app with a supported server such as Gunicorn or uWSGI, the
following response is rendered to a ``GET /example/item%2F001?p=value``:

.. code:: json

    {
        "path": "item/001"
    }

If we removed ``RawPathComponent()`` from the app's initializer, the request
would be routed as ``/example/item/001``, and no matching resource could be
found:

.. code:: json

    {
        "title": "404 Not Found"
    }

ASGI
----

The ASGI version of :attr:`req.path <falcon.asgi.Request.path>` uses the
``path`` key from the ASGI scope, where percent-encoded sequences are already
decoded into characters just like in WSGI's ``PATH_INFO``.
Similar to the WSGI snippet from the previous chapter, let us create a
middleware component that replaces ``req.path`` with the value of ``raw_path``
(provided the latter is present in the ASGI HTTP scope):

.. code:: python

    import falcon.asgi


    class RawPathComponent:
        async def process_request(self, req, resp):
            raw_path = req.scope.get('raw_path')

            # NOTE: Decode the tunneled raw path from the raw_path bytestring.
            if raw_path:
                req.path = raw_path.decode('latin1')


    class PathResource:
        async def on_get(self, req, resp, path):
            # NOTE: path here is potentially percent-encoded.
            path = falcon.uri.decode(path)

            resp.media = {'path': path}


    app = falcon.asgi.App(middleware=[RawPathComponent()])
    app.add_route('/example/{path}', PathResource())

Running the above snippet with ``uvicorn`` (that supports ``raw_path``), the
percent-encoded ``path`` field is now correctly handled for a
``GET /example/item%2F001?p=value`` request:

.. code:: json

    {
        "path": "item/001"
    }
