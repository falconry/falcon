.. _testing:

Testing Helpers
===============

.. automodule:: falcon.testing
    :noindex:

Simulating Requests
-------------------

Main Interface
~~~~~~~~~~~~~~

.. autoclass:: TestClient
   :members:
.. autoclass:: ASGIConductor
   :members:
.. autoclass:: Result
   :members:
   :inherited-members:
.. autoclass:: StreamedResult
   :members:
   :inherited-members:
.. autoclass:: ResultBodyStream
   :members:
.. autoclass:: ASGIWebSocketSimulator
   :members:
.. autoclass:: Cookie
   :members:

.. _testing_standalone_methods:

Standalone Methods
~~~~~~~~~~~~~~~~~~

.. autofunction:: simulate_get
.. autofunction:: simulate_head
.. autofunction:: simulate_post
.. autofunction:: simulate_put
.. autofunction:: simulate_options
.. autofunction:: simulate_patch
.. autofunction:: simulate_delete
.. autofunction:: simulate_request

.. autofunction:: capture_responder_args
.. autofunction:: capture_responder_args_async
.. autofunction:: set_resp_defaults
.. autofunction:: set_resp_defaults_async

Low-Level Utils
~~~~~~~~~~~~~~~

.. autoclass:: StartResponseMock
   :members:
.. autoclass:: ASGIRequestEventEmitter
   :members:
.. autoclass:: ASGILifespanEventEmitter
   :members:
.. autoclass:: ASGIResponseEventCollector
   :members:
.. autofunction:: create_environ
.. autofunction:: create_scope
.. autofunction:: create_scope_ws
.. autofunction:: create_req
.. autofunction:: create_asgi_req
.. autofunction:: closed_wsgi_iterable

Other Helpers
-------------

Test Cases
~~~~~~~~~~

.. autoclass:: TestCase
   :members:
.. autoclass:: SimpleTestResource
   :members:

Functions
~~~~~~~~~

.. autofunction:: rand_string
.. autofunction:: get_unused_port
.. autofunction:: redirected
.. autofunction:: get_encoding_from_headers
