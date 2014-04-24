.. _errors:

Error Handling
==============

When something goes horribly (or mildly) wrong, you *could* manually set the
error status, appropriate response headers, and even an error body using the
``resp`` object. However, Falcon tries to make things a bit easier by
providing a set of exceptions you can raise when something goes wrong. In fact,
if Falcon catches any exception your responder throws that inherits from
``falcon.HTTPError``, the framework will convert that exception to an
appropriate HTTP error response.

You may raise an instance of ``falcon.HTTPError`` directly, or use any one
of a number of predefined error classes that try to be idiomatic in
setting appropriate headers and bodies.

Base Class
----------

.. autoclass:: falcon.HTTPError
    :members:

Predefined Errors
-----------------

.. automodule:: falcon.exceptions
    :members:
    :member-order: bysource
