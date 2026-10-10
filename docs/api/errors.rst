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

.. tab-set::

    .. tab-item:: WSGI

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

    .. tab-item:: ASGI

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

.. _error_effect_on_resp:

How raising ``HTTPError`` / ``HTTPStatus`` affects ``resp``
-----------------------------------------------------------

When a responder, hook, or middleware component raises
:class:`~falcon.HTTPError` or :class:`~falcon.HTTPStatus`, Falcon's default
handlers compose the outgoing response from the exception **and** from any
headers or cookies already present on ``resp``. The body fields are treated
differently from headers:

**Body.** Immediately before the matching error handler runs, Falcon resets
:attr:`~falcon.Response.text`, :attr:`~falcon.Response.data`, and
:attr:`~falcon.Response.media` to ``None``. The default
:class:`~falcon.HTTPError` serializer then writes a new body (typically via
``resp.data`` or ``resp.media``). For :class:`~falcon.HTTPStatus`, the
handler assigns :attr:`~falcon.HTTPStatus.text` to ``resp.text`` (which may
be ``None`` when you only need a status line and headers, such as a
redirect).

**Headers and cookies.** Existing response headers and cookies are **not**
cleared. Any mapping passed as the exception's ``headers`` argument is applied
with :meth:`~falcon.Response.set_headers`, so matching header names overwrite
prior values while unrelated headers (and cookies set via
:meth:`~falcon.Response.set_cookie`) remain. This is useful when middleware
has already attached tracing headers or session cookies that should still be
sent with an error or redirect.

.. warning::
    Do not put ``Set-Cookie`` in the exception ``headers`` mapping.
    :meth:`~falcon.Response.set_headers` raises
    :class:`~falcon.errors.HeaderNotSupported` for that name. Set cookies on
    ``resp`` with :meth:`~falcon.Response.set_cookie` (or
    :meth:`~falcon.Response.append_header`) before raising, or from a custom
    error handler.

Example — cookies and custom headers survive an error response::

    class OrderResource:
        def on_get(self, req, resp, order_id):
            resp.set_header('X-Request-Id', req.context.request_id)
            resp.set_cookie('sid', req.context.session_id)
            resp.media = {'order_id': order_id}  # discarded if we raise below

            order = self._store.get(order_id)
            if order is None:
                raise falcon.HTTPNotFound(
                    title='Order not found',
                    headers={'X-Error-Code': 'order_missing'},
                )

            resp.media = order.to_dict()

See also :ref:`faq_resp_on_httperror` and :class:`~falcon.HTTPStatus`.

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

.. autoclass:: falcon.HTTPContentTooLarge
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
