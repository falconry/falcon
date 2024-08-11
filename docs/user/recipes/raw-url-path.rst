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

.. literalinclude:: ../../../examples/recipes/raw_url_path_wsgi.py
    :language: python

Running the above app with a supported server such as Gunicorn or uWSGI, the
following response is rendered to
a ``GET /cache/http%3A%2F%2Ffalconframework.org`` request:

.. code:: json

    {
        "url": "http://falconframework.org"
    }

We can also check the status of this URI in our imaginary web caching system by
accessing ``/cache/http%3A%2F%2Ffalconframework.org/status``:

.. code:: json

    {
        "cached": true
    }

If we removed ``RawPathComponent()`` from the app's middleware list, the
request would be routed as ``/cache/http://falconframework.org``, and no
matching resource would be found:

.. code:: json

    {
        "title": "404 Not Found"
    }

What is more, even if we could implement a flexible router that was capable of
matching these complex URI patterns, the app would still not be able to
distinguish between ``/cache/http%3A%2F%2Ffalconframework.org%2Fstatus`` and
``/cache/http%3A%2F%2Ffalconframework.org/status`` if both were presented only
in the percent-decoded form.

ASGI
----

The ASGI version of :attr:`req.path <falcon.asgi.Request.path>` uses the
``path`` key from the ASGI scope, where percent-encoded sequences are already
decoded into characters just like in WSGI's ``PATH_INFO``.
Similar to the WSGI snippet from the previous chapter, let us create a
middleware component that replaces ``req.path`` with the value of ``raw_path``
(provided the latter is present in the ASGI HTTP scope):

.. literalinclude:: ../../../examples/recipes/raw_url_path_asgi.py
    :language: python

Running the above snippet with ``uvicorn`` (that supports ``raw_path``), the
percent-encoded ``url`` field is now correctly handled for a
``GET /cache/http%3A%2F%2Ffalconframework.org%2Fstatus``
request:

.. code:: json

    {
        "url": "http://falconframework.org/status"
    }

Again, as in the WSGI version, removing ``RawPathComponent()`` no longer lets
the app route the above request as intended:

.. code:: json

    {
        "title": "404 Not Found"
    }
