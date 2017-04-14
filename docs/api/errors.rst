.. _errors:

Error Handling
==============

When it comes to error handling, you can always directly set the error
status, appropriate response headers, and error body using the ``resp``
object. However, Falcon tries to make things a little easier by
providing a set of error classes you can raise when something goes
wrong. All of these classes inherit from :class:`~.HTTPError`.

Falcon will convert any instance or subclass of :class:`~.HTTPError`
raised by a responder, hook, or middleware component into an appropriate
HTTP response. The default error serializer supports both JSON and XML.
If the client indicates acceptance of both JSON and XML with equal
weight, JSON will be chosen. Other media types may be supported by
overriding the default serializer via
:meth:`~.API.set_error_serializer`.

.. note::

    If a custom media type is used and the type includes a "+json" or
    "+xml" suffix, the default serializer will convert the error to JSON
    or XML, respectively.

All classes are available directly in the ``falcon`` package namespace::

    import falcon

    class MessageResource(object):
        def on_get(self, req, resp):

            # ...

            raise falcon.HTTPBadRequest(
                'TTL Out of Range',
                'The message's TTL must be between 60 and 300 seconds, inclusive.'
            )

            # ...

Note also that any exception (not just instances of
:class:`~.HTTPError`) can be caught, logged, and otherwise handled
at the global level by registering one or more custom error handlers.
See also :meth:`~.API.add_error_handler` to learn more about this
feature.

Base Class
----------

.. autoclass:: falcon.HTTPError
    :members:

Mixins
------

.. autoclass:: falcon.http_error.NoRepresentation
    :members:

.. _predefined_errors:

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
