.. _errors:

Error Handling
==============

When a request results in an error condition, you *could* manually set the
error status, appropriate response headers, and even an error body using the
``resp`` object. However, Falcon tries to make things a bit easier and more
consistent by providing a set of error classes you can raise from within
your app. Falcon catches any exception that inherits from
``falcon.HTTPError``, and automatically converts it to an appropriate HTTP
response.

You may raise an instance of ``falcon.HTTPError`` directly, or use any one
of a number of predefined error classes that try to be idiomatic in
setting appropriate headers and bodies.

Base Class
----------

.. autoclass:: falcon.HTTPError
    :members:

Mixins
------

.. autoclass:: falcon.http_error.NoRepresentation
    :members:

Predefined Errors
-----------------

.. automodule:: falcon
    :members: HTTPInvalidHeader, HTTPMissingHeader,
        HTTPInvalidParam, HTTPMissingParam,
        HTTPBadRequest, HTTPUnauthorized, HTTPForbidden, HTTPNotFound,
        HTTPMethodNotAllowed, HTTPNotAcceptable, HTTPConflict,
        HTTPLengthRequired, HTTPPreconditionFailed, HTTPUnsupportedMediaType,
        HTTPRangeNotSatisfiable, HTTPInternalServerError, HTTPBadGateway,
        HTTPServiceUnavailable,
