.. _testing:

Testing Helpers
===============

* `General Helpers`_
* `Simulating Requests`_
    * `Main Interface`_
    * `Low-Level Utils`_

.. automodule:: falcon.testing
    :noindex:

.. TODO: Add TOC here, and to other large RSTs?

General Helpers
---------------

.. autoclass:: TestCase
.. autoclass:: SimpleTestResource

.. autofunction:: invoke_coroutine_sync
.. autofunction:: rand_string
.. autofunction:: get_unused_port
.. autofunction:: redirected
.. autofunction:: get_encoding_from_headers


Simulating Requests
-------------------

Main Interface
~~~~~~~~~~~~~~

.. autofunction:: simulate_get
.. autofunction:: simulate_head
.. autofunction:: simulate_post
.. autofunction:: simulate_put
.. autofunction:: simulate_options
.. autofunction:: simulate_patch
.. autofunction:: simulate_delete
.. autofunction:: simulate_request

.. autoclass:: Result
.. autoclass:: Cookie
.. autoclass:: TestClient
.. autofunction:: capture_responder_args

Low-Level Utils
~~~~~~~~~~~~~~~

.. autoclass:: StartResponseMock
.. autoclass:: ASGIRequestEventEmitter
.. autoclass:: ASGILifespanEventEmitter
.. autoclass:: ASGIResponseEventCollector
.. autofunction:: create_environ
.. autofunction:: create_scope
.. autofunction:: create_req
.. autofunction:: create_asgi_req
.. autofunction:: closed_wsgi_iterable
