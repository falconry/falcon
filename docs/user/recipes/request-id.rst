.. _request-id-recipe:

Request ID Logging
==================

When things go wrong, it's important to be able to identify
all relevant log messages for a particular request. This is commonly done
by generating a unique ID for each request and then adding that ID
to every log entry.

If you wish to trace each request throughout your application, including
from within components that are deeply nested or otherwise live outside of the
normal request context, you can use a :class:`~contextvars.ContextVar` object
to store the request ID:

.. literalinclude:: ../../../examples/recipes/request_id_context.py
    :caption: *context.py*
    :language: python

Then, you can create a :ref:`middleware <middleware>` class to generate a
unique ID for each request, persisting it in the `contextvars` object:

.. literalinclude:: ../../../examples/recipes/request_id_middleware.py
    :caption: *middleware.py*
    :language: python

Alternatively, if all of your application logic has access to the
:ref:`request <request>`, you can simply use the
:attr:`req.context <falcon.Request.context>` object to store the ID:

.. literalinclude:: ../../../examples/recipes/request_id_structlog.py
    :caption: *middleware.py*
    :language: python

.. note::
    If your app is deployed behind a reverse proxy that injects a request ID
    header, you can easily adapt this recipe to use the upstream ID rather than
    generating a new one. By doing so, you can provide traceability across the
    entire request path.

    With this in mind, you may also wish to include this ID in any requests to
    downstream services.

Once you have access to a request ID, you can include it in your logs by
subclassing :class:`logging.Formatter` and overriding the ``format()`` method,
or by using a third-party logging library such as
`structlog <https://pypi.org/project/structlog/>`_ as demonstrated above.

In a pinch, you can also output the request ID directly:

.. literalinclude:: ../../../examples/recipes/request_id_log.py
    :caption: *some_other_module.py*
    :language: python

.. _contextvars: https://docs.python.org/3/library/contextvars.html
