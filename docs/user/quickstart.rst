.. _quickstart:

Quickstart
==========

If you haven't done so already, please take a moment to
:ref:`install <install>` the Falcon web framework before
continuing.

Learning by Example
-------------------

Here is a simple example from Falcon's README, showing how to get
started writing an app.

.. tabs::

    .. group-tab:: WSGI

        .. literalinclude:: ../../examples/things.py
            :language: python

        You can run the above example directly using the included wsgiref server:

        .. code:: bash

            $ pip install falcon
            $ python things.py

        Then, in another terminal:

        .. code:: bash

            $ curl localhost:8000/things

        As an alternative to Curl, you might want to give
        `HTTPie <https://github.com/jkbr/httpie>`_ a try:

        .. code:: bash

            $ pip install --upgrade httpie
            $ http localhost:8000/things

    .. group-tab:: ASGI

        .. literalinclude:: ../../examples/things_asgi.py
            :language: python

        You can run the ASGI version with uvicorn or any other ASGI server:

        .. code:: bash

            $ pip install falcon uvicorn
            $ uvicorn things_asgi:app

        Then, in another terminal:

        .. code:: bash

            $ curl localhost:8000/things

        As an alternative to Curl, you might want to give
        `HTTPie <https://github.com/jkbr/httpie>`_ a try:

        .. code:: bash

            $ pip install --upgrade httpie
            $ http localhost:8000/things

.. _quickstart-more-features:

A More Complex Example
----------------------

Here is a more involved example that demonstrates reading headers and query
parameters, handling errors, and working with request and response bodies.

.. tabs::

    .. group-tab:: WSGI

        Note that this example assumes that the
        `requests <https://pypi.org/project/requests/>`_ package has been installed.

        .. literalinclude:: ../../examples/things_advanced.py
            :language: python

        Again this code uses wsgiref, but you can also run the above example using
        any WSGI server, such as uWSGI or Gunicorn. For example:

        .. code:: bash

            $ pip install requests gunicorn
            $ gunicorn things:app

        On Windows you can run Gunicorn and uWSGI via WSL, or you might try Waitress:

        .. code:: bash

            $ pip install requests waitress
            $ waitress-serve --port=8000 things:app


        To test this example go to the another terminal and run:

        .. code:: bash

            $ http localhost:8000/1/things authorization:custom-token

        To visualize the application configuration the :ref:`inspect` can be used:

        .. code:: bash

            falcon-inspect-app things_advanced:app

        This would print for this example application:

        .. code::

            Falcon App (WSGI)
            • Routes:
                ⇒ /{user_id}/things - ThingsResource:
                   ├── GET - on_get
                   └── POST - on_post
            • Middleware (Middleware are independent):
                → AuthMiddleware.process_request
                  → RequireJSON.process_request
                    → JSONTranslator.process_request

                        ├── Process route responder

                    ↢ JSONTranslator.process_response
            • Sinks:
                ⇥ /search/(?P<engine>ddg|y)\Z SinkAdapter
            • Error handlers:
                ⇜ StorageError handle

    .. group-tab:: ASGI

        Note that this example requires the
        `httpx <https://pypi.org/project/httpx/>`_ package in lieu of
        `requests <https://pypi.org/project/requests/>`_.

        .. literalinclude:: ../../examples/things_advanced_asgi.py
            :language: python

        You can run the ASGI version with any ASGI server, such as uvicorn:

        .. code:: bash

            $ pip install falcon httpx uvicorn
            $ uvicorn things_advanced_asgi:app
