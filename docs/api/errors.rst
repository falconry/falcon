.. _errors:

Error Handling
==============

.. contents:: :local:

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
:meth:`~.App.set_error_serializer`.

.. note::

    If a custom media type is used and the type includes a "+json" or
    "+xml" suffix, the default serializer will convert the error to JSON
    or XML, respectively.

To customize what data is passed to the serializer, subclass
:class:`~.HTTPError` or any of its child classes, and override the
:meth:`~.HTTPError.to_dict` method. To also support XML, override the
:meth:`~.HTTPError.to_xml` method. For example::

    class HTTPNotAcceptable(falcon.HTTPNotAcceptable):

        def __init__(self, acceptable):
            description = (
                'Please see "acceptable" for a list of media types '
                'and profiles that are currently supported.'
            )

            super().__init__(description=description)
            self._acceptable = acceptable

        def to_dict(self, obj_type=dict):
            result = super().to_dict(obj_type)
            result['acceptable'] = self._acceptable
            return result

All classes are available directly in the ``falcon`` package namespace:

.. tabs::

    .. tab:: WSGI

        .. code:: python

            import falcon

            class MessageResource:
                def on_get(self, req, resp):

                    # -- snip --

                    raise falcon.HTTPBadRequest(
                        title="TTL Out of Range",
                        description="The message's TTL must be between 60 and 300 seconds, inclusive."
                    )

                    # -- snip --

    .. tab:: ASGI

        .. code:: python

            import falcon

            class MessageResource:
                async def on_get(self, req, resp):

                    # -- snip --

                    raise falcon.HTTPBadRequest(
                        title="TTL Out of Range",
                        description="The message's TTL must be between 60 and 300 seconds, inclusive."
                    )

                    # -- snip --

Note also that any exception (not just instances of
:class:`~.HTTPError`) can be caught, logged, and otherwise handled
at the global level by registering one or more custom error handlers.
See also :meth:`~.falcon.App.add_error_handler` to learn more about this
feature.

.. note::
    By default, any uncaught exceptions will return an HTTP 500 response and
    log details of the exception to ``wsgi.errors``.

Base Class
----------

.. autoclass:: falcon.HTTPError
    :members:

.. _predefined_errors:

Predefined Errors
-----------------

.. autoclass:: falcon.HTTPBadRequest
    :members:

.. autoclass:: falcon.HTTPInvalidHeader
    :members:

.. autoclass:: falcon.HTTPMissingHeader
    :members:

.. autoclass:: falcon.HTTPInvalidParam
    :members:

.. autoclass:: falcon.HTTPMissingParam
    :members:

.. autoclass:: falcon.HTTPUnauthorized
    :members:

.. autoclass:: falcon.HTTPForbidden
    :members:

.. autoclass:: falcon.HTTPNotFound
    :members:

.. autoclass:: falcon.HTTPRouteNotFound
    :members:

.. autoclass:: falcon.HTTPMethodNotAllowed
    :members:

.. autoclass:: falcon.HTTPNotAcceptable
    :members:

.. autoclass:: falcon.HTTPConflict
    :members:

.. autoclass:: falcon.HTTPGone
    :members:

.. autoclass:: falcon.HTTPLengthRequired
    :members:

.. autoclass:: falcon.HTTPPreconditionFailed
    :members:

.. autoclass:: falcon.HTTPPayloadTooLarge
    :members:

.. autoclass:: falcon.HTTPUriTooLong
    :members:

.. autoclass:: falcon.HTTPUnsupportedMediaType
    :members:

.. autoclass:: falcon.HTTPRangeNotSatisfiable
    :members:

.. autoclass:: falcon.HTTPUnprocessableEntity
    :members:

.. autoclass:: falcon.HTTPLocked
    :members:

.. autoclass:: falcon.HTTPFailedDependency
    :members:

.. autoclass:: falcon.HTTPPreconditionRequired
    :members:

.. autoclass:: falcon.HTTPTooManyRequests
    :members:

.. autoclass:: falcon.HTTPRequestHeaderFieldsTooLarge
    :members:

.. autoclass:: falcon.HTTPUnavailableForLegalReasons
    :members:

.. autoclass:: falcon.HTTPInternalServerError
    :members:

.. autoclass:: falcon.HTTPNotImplemented
    :members:

.. autoclass:: falcon.HTTPBadGateway
    :members:

.. autoclass:: falcon.HTTPServiceUnavailable
    :members:

.. autoclass:: falcon.HTTPGatewayTimeout
    :members:

.. autoclass:: falcon.HTTPVersionNotSupported
    :members:

.. autoclass:: falcon.HTTPInsufficientStorage
    :members:

.. autoclass:: falcon.HTTPLoopDetected
    :members:

.. autoclass:: falcon.HTTPNetworkAuthenticationRequired
    :members:

.. autoclass:: falcon.MediaNotFoundError
    :members:

.. autoclass:: falcon.MediaMalformedError
    :members:

.. autoclass:: falcon.MediaValidationError
    :members:
