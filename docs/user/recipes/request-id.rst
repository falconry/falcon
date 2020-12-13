.. _request-id-recipe:

Request ID Logging
==================

When things go wrong, it's important to be able to identify
all relevant log messages for a particular request. This is commonly done
by generating a unique ID for each request and then adding that ID
to every log entry.

If you wish to trace each request throughout your application, including
from within components that are deeply nested or otherwise live outside of the
normal request context, you can use a `thread-local`_ context object to store
the request ID:

.. code:: python

    # context.py

    import threading

    class _Context:
        def __init__(self):
            self._thread_local = threading.local()

        @property
        def request_id(self):
            return getattr(self._thread_local, 'request_id', None)

        @request_id.setter
        def request_id(self, value):
            self._thread_local.request_id = value

    ctx = _Context()

Then, you can create a :ref:`middleware <middleware>` class to generate a
unique ID for each request, persisting it in the thread local:

.. code:: python

    # middleware.py

    from uuid import uuid4
    from context import ctx

    class RequestIDMiddleware:
        def process_request(self, req, resp):
            ctx.request_id = str(uuid4())

        # It may also be helpful to include the ID in the response
        def process_response(self, req, resp, resource, req_succeeded):
            resp.set_header('X-Request-ID', ctx.request_id)

Alternatively, if all of your application logic has access to the :ref:`request
<request>`, you can simply use the `context` object to store the ID:

.. code:: python

    # middleware.py

    from uuid import uuid4

    # Optional logging package (pip install structlog)
    import structlog

    class RequestIDMiddleware:
        def process_request(self, req, resp):
            request_id = str(uuid4())

            # Using Falcon 2.0 syntax
            req.context.request_id = request_id

            # Or if your logger has built-in support for contexts
            req.context.log = structlog.get_logger(request_id=request_id)

        # It may also be helpful to include the ID in the response
        def process_response(self, req, resp, resource, req_succeeded):
            resp.set_header('X-Request-ID', req.context.request_id)

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

.. code:: python

    # some_other_module.py

    import logging

    from context import ctx

    def create_widget_object(name: str) -> Any:
        request_id = 'request_id={0}'.format(ctx.request_id)
        logging.debug('%s going to create widget: %s', request_id, name)

        try:
            # create the widget
        except:
            logging.exception('%s something went wrong', request_id)

        logging.debug('%s created widget: %s', request_id, name)


.. _thread-local: https://docs.python.org/3.7/library/threading.html#thread-local-data
