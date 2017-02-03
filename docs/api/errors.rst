.. _errors:

Error Handling
==============

When a request results in an error condition, you can manually set the
error status, appropriate response headers, and even an error body using the
``resp`` object. However, Falcon tries to make things a bit easier and more
consistent by providing a set of error classes you can raise from within
your app. Falcon catches any exception that inherits from
``falcon.HTTPError``, and automatically converts it to an appropriate HTTP
response.

You may raise an instance of ``falcon.HTTPError`` directly, or use any one
of a number of predefined error classes that try to be idiomatic in
setting appropriate headers and bodies.

All classes are available directly from the `falcon` package namespace::

    import falcon

    class MessageResource(object):
        def on_get(self, req, resp):

            # ...

            raise falcon.HTTPBadRequest(
                'TTL Out of Range',
                'The message's TTL must be between 60 and 300 seconds, inclusive.'
            )

            # ...

The default error serializer supports JSON and XML. You can override the
default serializer by passing a callable to the :class:`~.API` method,
:meth:`~.API.set_error_serializer`.

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
    :members: HTTPBadRequest,
        HTTPInvalidHeader, HTTPMissingHeader,
        HTTPInvalidParam, HTTPMissingParam,
        HTTPUnauthorized, HTTPForbidden, HTTPNotFound, HTTPMethodNotAllowed,
        HTTPNotAcceptable, HTTPConflict, HTTPGone, HTTPLengthRequired,
        HTTPPreconditionFailed, HTTPRequestEntityTooLarge, HTTPUriTooLong,
        HTTPUnsupportedMediaType, HTTPRangeNotSatisfiable,
        HTTPUnprocessableEntity, HTTPLocked, HTTPFailedDependency,
        HTTPPreconditionRequired, HTTPTooManyRequests,
        HTTPRequestHeaderFieldsTooLarge,
        HTTPUnavailableForLegalReasons,
        HTTPInternalServerError, HTTPBadGateway, HTTPServiceUnavailable,
        HTTPInsufficientStorage, HTTPLoopDetected,
        HTTPNetworkAuthenticationRequired
