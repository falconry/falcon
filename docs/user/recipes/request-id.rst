.. _request-id-recipe:

Request ID Logging
==================

To assist debugging when things go wrong it is helpful to find the relevant
logs for a particular request. One way to do this is generate a unique request
ID for each request and to add that to every log message.

If you wish to trace the request throughout the application such as within
data manipulations that are outside of the request context. You can use a
`thread-local`_ context object to store the request ID:

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

Now you can create a :ref:`middleware <middleware>` class that you can
create a unique ID and set that in the thread local:

.. code:: python

    # middleware.py

    from uuid import uuid4
    from context import ctx

    class RequestIDMiddleware:
        def process_request(self, req, resp):
            ctx.request_id = str(uuid4())


Alternatively if all of your application logic has access to the
:ref:`request <request>` you can use the `context` object to store the ID.

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

Logging with the `thread-local`_ context can be done like:

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
