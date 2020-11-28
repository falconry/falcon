.. _rr:

Request & Response
==================

Similar to other frameworks, Falcon employs the inversion of control (IoC)
pattern to coordinate with app methods in order to respond to HTTP requests.
Resource responders, middleware methods, hooks, etc. receive a reference to the
request and response objects that represent the current in-flight HTTP request.
The app can use these objects to inspect the incoming HTTP request, and to
manipulate the outgoing HTTP response.

Falcon uses different types to represent HTTP requests and
responses for WSGI (:class:`falcon.App`) vs. ASGI (:class:`falcon.asgi.App`).
However, the two interfaces are designed to be as similar as possible to
minimize confusion and to facilitate porting.

(See also: :ref:`routing`)

.. toctree::
   :maxdepth: 2

   request_and_response_wsgi
   request_and_response_asgi
