# Copyright 2013 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""HTTP error classes and other Falcon-specific errors.

This module implements a collection of `falcon.HTTPError`
specializations that can be raised to generate a 4xx or 5xx HTTP
response. All classes are available directly from the `falcon`
package namespace::

    import falcon

    class MessageResource:
        def on_get(self, req, resp):

            # -- snip --

            raise falcon.HTTPBadRequest(
                title='TTL Out of Range',
                description='The message's TTL must be between 60 and 300 seconds.'
            )

            # -- snip --
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional, TYPE_CHECKING, Union

from falcon.http_error import HTTPError
import falcon.status_codes as status
from falcon.util import deprecation
from falcon.util.misc import dt_to_http

if TYPE_CHECKING:
    from falcon._typing import HeaderArg
    from falcon.typing import Headers


__all__ = (
    'CompatibilityError',
    'DelimiterError',
    'HeaderNotSupported',
    'HTTPBadGateway',
    'HTTPBadRequest',
    'HTTPConflict',
    'HTTPFailedDependency',
    'HTTPForbidden',
    'HTTPGatewayTimeout',
    'HTTPGone',
    'HTTPInsufficientStorage',
    'HTTPInternalServerError',
    'HTTPInvalidHeader',
    'HTTPInvalidParam',
    'HTTPLengthRequired',
    'HTTPLocked',
    'HTTPLoopDetected',
    'HTTPMethodNotAllowed',
    'HTTPMissingHeader',
    'HTTPMissingParam',
    'HTTPNetworkAuthenticationRequired',
    'HTTPNotAcceptable',
    'HTTPNotFound',
    'HTTPNotImplemented',
    'HTTPContentTooLarge',
    'HTTPPreconditionFailed',
    'HTTPPreconditionRequired',
    'HTTPRangeNotSatisfiable',
    'HTTPRequestHeaderFieldsTooLarge',
    'HTTPRouteNotFound',
    'HTTPServiceUnavailable',
    'HTTPTooManyRequests',
    'HTTPUnauthorized',
    'HTTPUnavailableForLegalReasons',
    'HTTPUnprocessableEntity',
    'HTTPUnsupportedMediaType',
    'HTTPUriTooLong',
    'HTTPVersionNotSupported',
    'InvalidMediaRange',
    'InvalidMediaType',
    'MediaMalformedError',
    'MediaNotFoundError',
    'MediaValidationError',
    'MultipartParseError',
    'OperationNotAllowed',
    'PayloadTypeError',
    'UnsupportedError',
    'UnsupportedScopeError',
    'WebSocketDisconnected',
    'WebSocketHandlerNotFound',
    'WebSocketPathNotFound',
    'WebSocketServerError',
)


class HeaderNotSupported(ValueError):
    """The specified header is not supported by this method."""


class CompatibilityError(ValueError):
    """The given method, value, or type is not compatible."""


class InvalidMediaType(ValueError):
    """The provided media type cannot be parsed into type/subtype."""


class InvalidMediaRange(InvalidMediaType):
    """The media range contains an invalid media type and/or the q value."""


class UnsupportedScopeError(RuntimeError):
    """The ASGI scope type is not supported by Falcon."""


class UnsupportedError(RuntimeError):
    """The method or operation is not supported."""


# NOTE(kgriffs): This inherits from ValueError to be consistent with the type
#   raised by Python's built-in file-like objects.
class OperationNotAllowed(ValueError):
    """The requested operation is not allowed."""


class DelimiterError(IOError):
    """The read operation did not find the requested stream delimiter."""


class PayloadTypeError(TypeError):
    """The WebSocket message payload was not of the expected type."""


class WebSocketDisconnected(ConnectionError):
    """The websocket connection is lost.

    This error is raised when attempting to perform an operation on the
    WebSocket and it is determined that either the client has closed the
    connection, the server closed the connection, or the socket has otherwise
    been lost.

    Keyword Args:
        code (int): The WebSocket close code, as per the WebSocket spec
            (default ``1000``).
    """

    code: int
    """The WebSocket close code, as per the WebSocket spec."""

    def __init__(self, code: Optional[int] = None) -> None:
        self.code = code or 1000  # Default to "Normal Closure"


class WebSocketPathNotFound(WebSocketDisconnected):
    """No route could be found for the requested path.

    A simulated WebSocket connection was attempted but the path specified in
    the handshake request did not match any of the app's routes.
    """

    pass


class WebSocketHandlerNotFound(WebSocketDisconnected):
    """The routed resource does not contain an ``on_websocket()`` handler."""

    pass


class WebSocketServerError(WebSocketDisconnected):
    """The server encountered an unexpected error."""

    pass


HTTPErrorKeywordArguments = Union[str, int, None]

# TODO(vytas): Passing **kwargs down to HTTPError results in arg-type error in
#   Mypy, because it is impossible to verify that, e.g., an int value was not
#   erroneously passed to href instead of code, etc.
#
#   It is hard to properly type this on older Pythons, so we just sprinkle type
#   ignores on the super().__init__(...) calls below. In any case, this call is
#   internal to the framework.
#
#   On Python 3.11+, I have verified it is possible to properly type this
#   pattern using typing.Unpack:
#
#   class HTTPErrorKeywordArguments(TypedDict):
#       href: Optional[str]
#       href_text: Optional[str]
#       code: Optional[int]
#
#   class HTTPErrorSubclass(HTTPError):
#       def __init__(
#           self,
#           *,
#           title: Optional[str] = None,
#           description: Optional[str] = None,
#           headers: Optional[HeaderList] = None,
#           **kwargs: Unpack[HTTPErrorKeywordArguments],
#       ) -> None:
#           super().__init__(
#               status.HTTP_400,
#               title=title,
#               description=description,
#               headers=headers,
#               **kwargs,
#           )

RetryAfter = Union[int, datetime, None]


class HTTPBadRequest(HTTPError):
    """400 Bad Request.

    The server cannot or will not process the request due to something
    that is perceived to be a client error (e.g., malformed request
    syntax, invalid request message framing, or deceptive request
    routing).

    (See also: RFC 7231, Section 6.5.1)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '400 Bad Request').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ) -> None:
        super().__init__(
            status.HTTP_400,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPUnauthorized(HTTPError):
    """401 Unauthorized.

    The request has not been applied because it lacks valid
    authentication credentials for the target resource.

    The server generating a 401 response MUST send a WWW-Authenticate
    header field containing at least one challenge applicable to the
    target resource.

    If the request included authentication credentials, then the 401
    response indicates that authorization has been refused for those
    credentials. The user agent MAY repeat the request with a new or
    replaced Authorization header field. If the 401 response contains
    the same challenge as the prior response, and the user agent has
    already attempted authentication at least once, then the user agent
    SHOULD present the enclosed representation to the user, since it
    usually contains relevant diagnostic information.

    (See also: RFC 7235, Section 3.1)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '401 Unauthorized').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        challenges (iterable of str): One or more authentication
            challenges to use as the value of the WWW-Authenticate header in
            the response.

            Note:
                The existing value of the WWW-Authenticate in headers will be
                overridden by this value

            (See also: RFC 7235, Section 2.1)
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).

    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        challenges: Optional[Iterable[str]] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        if challenges:
            headers = _load_headers(headers)
            headers['WWW-Authenticate'] = ', '.join(challenges)

        super().__init__(
            status.HTTP_401,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPForbidden(HTTPError):
    """403 Forbidden.

    The server understood the request but refuses to authorize it.

    A server that wishes to make public why the request has been
    forbidden can describe that reason in the response payload (if any).

    If authentication credentials were provided in the request, the
    server considers them insufficient to grant access. The client
    SHOULD NOT automatically repeat the request with the same
    credentials. The client MAY repeat the request with new or different
    credentials. However, a request might be forbidden for reasons
    unrelated to the credentials.

    An origin server that wishes to "hide" the current existence of a
    forbidden target resource MAY instead respond with a status code of
    404 Not Found.

    (See also: RFC 7231, Section 6.5.4)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '403 Forbidden').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_403,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPNotFound(HTTPError):
    """404 Not Found.

    The origin server did not find a current representation for the
    target resource or is not willing to disclose that one exists.

    A 404 status code does not indicate whether this lack of
    representation is temporary or permanent; the 410 Gone status code
    is preferred over 404 if the origin server knows, presumably through
    some configurable means, that the condition is likely to be
    permanent.

    A 404 response is cacheable by default; i.e., unless otherwise
    indicated by the method definition or explicit cache controls.

    (See also: RFC 7231, Section 6.5.3)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Human-friendly error title. If not provided, and
            `description` is also not provided, no body will be included
            in the response.
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two (default ``None``).
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_404,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPRouteNotFound(HTTPNotFound):
    """404 Not Found.

    The request did not match any routes configured for the application.

    This subclass of :class:`~.HTTPNotFound` is raised by the framework to
    provide a default 404 response when no route matches the request. This
    behavior can be customized by registering a custom error handler for
    :class:`~.HTTPRouteNotFound`.

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Human-friendly error title. If not provided, and
            `description` is also not provided, no body will be included
            in the response.
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two (default ``None``).
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """


class HTTPMethodNotAllowed(HTTPError):
    """405 Method Not Allowed.

    The method received in the request-line is known by the origin
    server but not supported by the target resource.

    The origin server MUST generate an Allow header field in a 405
    response containing a list of the target resource's currently
    supported methods.

    A 405 response is cacheable by default; i.e., unless otherwise
    indicated by the method definition or explicit cache controls.

    (See also: RFC 7231, Section 6.5.5)

    `allowed_methods` is the only positional argument allowed,
    the other arguments are defined as keyword-only.

    Args:
        allowed_methods (list of str): Allowed HTTP methods for this
            resource (e.g., ``['GET', 'POST', 'HEAD']``).

            Note:
                If previously set, the Allow response header will be
                overridden by this value.

    Keyword Args:
        title (str): Human-friendly error title. If not provided, and
            `description` is also not provided, no body will be included
            in the response.
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two (default ``None``).
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        allowed_methods: Iterable[str],
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        headers = _load_headers(headers)
        headers['Allow'] = ', '.join(allowed_methods)
        super().__init__(
            status.HTTP_405,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPNotAcceptable(HTTPError):
    """406 Not Acceptable.

    The target resource does not have a current representation that
    would be acceptable to the user agent, according to the proactive
    negotiation header fields received in the request, and the server
    is unwilling to supply a default representation.

    The server SHOULD generate a payload containing a list of available
    representation characteristics and corresponding resource
    identifiers from which the user or user agent can choose the one
    most appropriate. A user agent MAY automatically select the most
    appropriate choice from that list. However, this specification does
    not define any standard for such automatic selection, as described
    in RFC 7231, Section 6.4.1

    (See also: RFC 7231, Section 6.5.6)

    All the arguments are defined as keyword-only.

    Keyword Args:
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_406,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPConflict(HTTPError):
    """409 Conflict.

    The request could not be completed due to a conflict with the
    current state of the target resource. This code is used in
    situations where the user might be able to resolve the conflict and
    resubmit the request.

    The server SHOULD generate a payload that includes enough
    information for a user to recognize the source of the conflict.

    Conflicts are most likely to occur in response to a PUT request. For
    example, if versioning were being used and the representation being
    PUT included changes to a resource that conflict with those made by
    an earlier (third-party) request, the origin server might use a 409
    response to indicate that it can't complete the request. In this
    case, the response representation would likely contain information
    useful for merging the differences based on the revision history.

    (See also: RFC 7231, Section 6.5.8)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '409 Conflict').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_409,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPGone(HTTPError):
    """410 Gone.

    The target resource is no longer available at the origin server and
    this condition is likely to be permanent.

    If the origin server does not know, or has no facility to determine,
    whether or not the condition is permanent, the status code 404 Not
    Found ought to be used instead.

    The 410 response is primarily intended to assist the task of web
    maintenance by notifying the recipient that the resource is
    intentionally unavailable and that the server owners desire that
    remote links to that resource be removed. Such an event is common
    for limited-time, promotional services and for resources belonging
    to individuals no longer associated with the origin server's site.
    It is not necessary to mark all permanently unavailable resources as
    "gone" or to keep the mark for any length of time -- that is left to
    the discretion of the server owner.

    A 410 response is cacheable by default; i.e., unless otherwise
    indicated by the method definition or explicit cache controls.

    (See also: RFC 7231, Section 6.5.9)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Human-friendly error title. If not provided, and
            `description` is also not provided, no body will be included
            in the response.
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two (default ``None``).
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_410,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPLengthRequired(HTTPError):
    """411 Length Required.

    The server refuses to accept the request without a defined Content-
    Length.

    The client MAY repeat the request if it adds a valid Content-Length
    header field containing the length of the message body in the
    request message.

    (See also: RFC 7231, Section 6.5.10)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '411 Length Required').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_411,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPPreconditionFailed(HTTPError):
    """412 Precondition Failed.

    One or more conditions given in the request header fields evaluated
    to false when tested on the server.

    This response code allows the client to place preconditions on the
    current resource state (its current representations and metadata)
    and, thus, prevent the request method from being applied if the
    target resource is in an unexpected state.

    (See also: RFC 7232, Section 4.2)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '412 Precondition Failed').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_412,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPContentTooLarge(HTTPError):
    """413 Content Too Large.

    The server is refusing to process a request because the request
    payload is larger than the server is willing or able to process.

    The server MAY close the connection to prevent the client from
    continuing the request.

    If the condition is temporary, the server SHOULD generate a Retry-
    After header field to indicate that it is temporary and after what
    time the client MAY try again.

    (See also: RFC 7231, Section 6.5.11)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '413 Payload Too Large').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        retry_after (datetime or int): Value for the Retry-After
            header. If a ``datetime`` object, will serialize as an HTTP date.
            Otherwise, a non-negative ``int`` is expected, representing the
            number of seconds to wait.

            Note:
                The existing value of the Retry-After in headers will be
                overridden by this value
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).

    .. versionadded:: 4.0
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        retry_after: RetryAfter = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ) -> None:
        super().__init__(
            status.HTTP_413,
            title=title,
            description=description,
            headers=_parse_retry_after(headers, retry_after),
            **kwargs,  # type: ignore[arg-type]
        )


# TODO(vytas): Remove in Falcon 5.0.
class HTTPPayloadTooLarge(HTTPContentTooLarge):
    """Compatibility alias of :class:`falcon.HTTPContentTooLarge`."""

    @deprecation.deprecated(
        'HTTPPayloadTooLarge is deprecated; use HTTPContentTooLarge instead.'
    )
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class HTTPUriTooLong(HTTPError):
    """414 URI Too Long.

    The server is refusing to service the request because the request-
    target is longer than the server is willing to interpret.

    This rare condition is only likely to occur when a client has
    improperly converted a POST request to a GET request with long query
    information, when the client has descended into a "black hole" of
    redirection (e.g., a redirected URI prefix that points to a suffix
    of itself) or when the server is under attack by a client attempting
    to exploit potential security holes.

    A 414 response is cacheable by default; i.e., unless otherwise
    indicated by the method definition or explicit cache controls.

    (See also: RFC 7231, Section 6.5.12)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '414 URI Too Long').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two (default ``None``).
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_414,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPUnsupportedMediaType(HTTPError):
    """415 Unsupported Media Type.

    The origin server is refusing to service the request because the
    payload is in a format not supported by this method on the target
    resource.

    The format problem might be due to the request's indicated Content-
    Type or Content-Encoding, or as a result of inspecting the data
    directly.

    (See also: RFC 7231, Section 6.5.13)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '415 Unsupported Media Type').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_415,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPRangeNotSatisfiable(HTTPError):
    """416 Range Not Satisfiable.

    None of the ranges in the request's Range header field overlap the
    current extent of the selected resource or that the set of ranges
    requested has been rejected due to invalid ranges or an excessive
    request of small or overlapping ranges.

    For byte ranges, failing to overlap the current extent means that
    the first-byte-pos of all of the byte-range-spec values were greater
    than the current length of the selected representation. When this
    status code is generated in response to a byte-range request, the
    sender SHOULD generate a Content-Range header field specifying the
    current length of the selected representation.

    (See also: RFC 7233, Section 4.4)

    `resource_length` is the only positional argument allowed,
    the other arguments are defined as keyword-only.

    Args:
        resource_length: The maximum value for the last-byte-pos of a range
            request. Used to set the Content-Range header.

            Note:
                The existing value of the Content-Range in headers will be
                overridden by this value

    Keyword Args:
        title (str): Error title (default '416 Range Not Satisfiable').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        resource_length: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        headers = _load_headers(headers)
        headers['Content-Range'] = 'bytes */' + str(resource_length)

        super().__init__(
            status.HTTP_416,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPUnprocessableEntity(HTTPError):
    """422 Unprocessable Entity.

    The server understands the content type of the request entity (hence
    a 415 Unsupported Media Type status code is inappropriate), and the
    syntax of the request entity is correct (thus a 400 Bad Request
    status code is inappropriate) but was unable to process the
    contained instructions.

    For example, this error condition may occur if an XML request body
    contains well-formed (i.e., syntactically correct), but semantically
    erroneous, XML instructions.

    (See also: RFC 4918, Section 11.2)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '422 Unprocessable Entity').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_422,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPLocked(HTTPError):
    """423 Locked.

    The 423 (Locked) status code means the source or destination resource
    of a method is locked. This response SHOULD contain an appropriate
    precondition or postcondition code, such as 'lock-token-submitted' or
    'no-conflicting-lock'.

    (See also: RFC 4918, Section 11.3)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '423 Locked').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_423,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPFailedDependency(HTTPError):
    """424 Failed Dependency.

    The 424 (Failed Dependency) status code means that the method could
    not be performed on the resource because the requested action
    depended on another action and that action failed.

    (See also: RFC 4918, Section 11.4)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '424 Failed Dependency').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_424,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPPreconditionRequired(HTTPError):
    """428 Precondition Required.

    The 428 status code indicates that the origin server requires the
    request to be conditional.

    Its typical use is to avoid the "lost update" problem, where a client
    GETs a resource's state, modifies it, and PUTs it back to the server,
    when meanwhile a third party has modified the state on the server,
    leading to a conflict.  By requiring requests to be conditional, the
    server can assure that clients are working with the correct copies.

    Responses using this status code SHOULD explain how to resubmit the
    request successfully.

    (See also: RFC 6585, Section 3)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '428 Precondition Required').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_428,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPTooManyRequests(HTTPError):
    """429 Too Many Requests.

    The user has sent too many requests in a given amount of time ("rate
    limiting").

    The response representations SHOULD include details explaining the
    condition, and MAY include a Retry-After header indicating how long
    to wait before making a new request.

    Responses with the 429 status code MUST NOT be stored by a cache.

    (See also: RFC 6585, Section 4)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '429 Too Many Requests').
        description (str): Human-friendly description of the rate limit that
            was exceeded.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        retry_after (datetime or int): Value for the Retry-After
            header. If a ``datetime`` object, will serialize as an HTTP date.
            Otherwise, a non-negative ``int`` is expected, representing the
            number of seconds to wait.

            Note:
                The existing value of the Retry-After in headers will be
                overridden by this value
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        retry_after: RetryAfter = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_429,
            title=title,
            description=description,
            headers=_parse_retry_after(headers, retry_after),
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPRequestHeaderFieldsTooLarge(HTTPError):
    """431 Request Header Fields Too Large.

    The 431 status code indicates that the server is unwilling to process
    the request because its header fields are too large.  The request MAY
    be resubmitted after reducing the size of the request header fields.

    It can be used both when the set of request header fields in total is
    too large, and when a single header field is at fault.  In the latter
    case, the response representation SHOULD specify which header field
    was too large.

    Responses with the 431 status code MUST NOT be stored by a cache.

    (See also: RFC 6585, Section 5)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '431 Request Header Fields Too Large').
        description (str): Human-friendly description of the rate limit that
            was exceeded.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_431,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPUnavailableForLegalReasons(HTTPError):
    """451 Unavailable For Legal Reasons.

    The server is denying access to the resource as a consequence of a
    legal demand.

    The server in question might not be an origin server. This type of
    legal demand typically most directly affects the operations of ISPs
    and search engines.

    Responses using this status code SHOULD include an explanation, in
    the response body, of the details of the legal demand: the party
    making it, the applicable legislation or regulation, and what
    classes of person and resource it applies to.

    Note that in many cases clients can still access the denied resource
    by using technical countermeasures such as a VPN or the Tor network.

    A 451 response is cacheable by default; i.e., unless otherwise
    indicated by the method definition or explicit cache controls.

    (See also: RFC 7725, Section 3)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '451 Unavailable For Legal Reasons').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two (default ``None``).
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_451,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPInternalServerError(HTTPError):
    """500 Internal Server Error.

    The server encountered an unexpected condition that prevented it
    from fulfilling the request.

    (See also: RFC 7231, Section 6.6.1)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '500 Internal Server Error').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).

    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_500,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPNotImplemented(HTTPError):
    """501 Not Implemented.

    The 501 (Not Implemented) status code indicates that the server does
    not support the functionality required to fulfill the request.  This
    is the appropriate response when the server does not recognize the
    request method and is not capable of supporting it for any resource.

    A 501 response is cacheable by default; i.e., unless otherwise
    indicated by the method definition or explicit cache controls
    as described in RFC 7234, Section 4.2.2.

    (See also: RFC 7231, Section 6.6.2)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '500 Internal Server Error').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.

        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).

    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_501,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPBadGateway(HTTPError):
    """502 Bad Gateway.

    The server, while acting as a gateway or proxy, received an invalid
    response from an inbound server it accessed while attempting to
    fulfill the request.

    (See also: RFC 7231, Section 6.6.3)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '502 Bad Gateway').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_502,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPServiceUnavailable(HTTPError):
    """503 Service Unavailable.

    The server is currently unable to handle the request due to a
    temporary overload or scheduled maintenance, which will likely be
    alleviated after some delay.

    The server MAY send a Retry-After header field to suggest an
    appropriate amount of time for the client to wait before retrying
    the request.

    Note: The existence of the 503 status code does not imply that a
    server has to use it when becoming overloaded. Some servers might
    simply refuse the connection.

    (See also: RFC 7231, Section 6.6.4)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '503 Service Unavailable').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        retry_after (datetime or int): Value for the Retry-After header. If a
            ``datetime`` object, will serialize as an HTTP date. Otherwise,
            a non-negative ``int`` is expected, representing the number of
            seconds to wait.

            Note:
                The existing value of the Retry-After in headers will be
                overridden by this value
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        retry_after: RetryAfter = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_503,
            title=title,
            description=description,
            headers=_parse_retry_after(headers, retry_after),
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPGatewayTimeout(HTTPError):
    """504 Gateway Timeout.

    The 504 (Gateway Timeout) status code indicates that the server,
    while acting as a gateway or proxy, did not receive a timely response
    from an upstream server it needed to access in order to complete the
    request.

    (See also: RFC 7231, Section 6.6.5)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '503 Service Unavailable').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_504,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPVersionNotSupported(HTTPError):
    """505 HTTP Version Not Supported.

    The 505 (HTTP Version Not Supported) status code indicates that the
    server does not support, or refuses to support, the major version of
    HTTP that was used in the request message.  The server is indicating
    that it is unable or unwilling to complete the request using the same
    major version as the client (as described in RFC 7230, Section 2.6),
    other than with this error message.  The server SHOULD
    generate a representation for the 505 response that describes why
    that version is not supported and what other protocols are supported
    by that server.

    (See also: RFC 7231, Section 6.6.6)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '503 Service Unavailable').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_505,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPInsufficientStorage(HTTPError):
    """507 Insufficient Storage.

    The 507 (Insufficient Storage) status code means the method could not
    be performed on the resource because the server is unable to store
    the representation needed to successfully complete the request. This
    condition is considered to be temporary. If the request that
    received this status code was the result of a user action, the
    request MUST NOT be repeated until it is requested by a separate user
    action.

    (See also: RFC 4918, Section 11.5)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '507 Insufficient Storage').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_507,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPLoopDetected(HTTPError):
    """508 Loop Detected.

    The 508 (Loop Detected) status code indicates that the server
    terminated an operation because it encountered an infinite loop while
    processing a request with "Depth: infinity". This status indicates
    that the entire operation failed.

    (See also: RFC 5842, Section 7.2)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '508 Loop Detected').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_508,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPNetworkAuthenticationRequired(HTTPError):
    """511 Network Authentication Required.

    The 511 status code indicates that the client needs to authenticate
    to gain network access.

    The response representation SHOULD contain a link to a resource that
    allows the user to submit credentials.

    Note that the 511 response SHOULD NOT contain a challenge or the
    authentication interface itself, because clients would show the
    interface as being associated with the originally requested URL,
    which may cause confusion.

    The 511 status SHOULD NOT be generated by origin servers; it is
    intended for use by intercepting proxies that are interposed as a
    means of controlling access to the network.

    Responses with the 511 status code MUST NOT be stored by a cache.

    (See also: RFC 6585, Section 6)

    All the arguments are defined as keyword-only.

    Keyword Args:
        title (str): Error title (default '511 Network Authentication Required').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        super().__init__(
            status.HTTP_511,
            title=title,
            description=description,
            headers=headers,
            **kwargs,  # type: ignore[arg-type]
        )


class HTTPInvalidHeader(HTTPBadRequest):
    """400 Bad Request.

    One of the headers in the request is invalid.

    `msg` and `header_name` are the only positional arguments allowed,
    the other arguments are defined as keyword-only.

    Args:
        msg (str): A description of why the value is invalid.
        header_name (str): The name of the invalid header.

    Keyword Args:
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        msg: str,
        header_name: str,
        *,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        description = 'The value provided for the "{0}" header is invalid. {1}'
        description = description.format(header_name, msg)

        super().__init__(
            title='Invalid header value',
            description=description,
            headers=headers,
            **kwargs,
        )


class HTTPMissingHeader(HTTPBadRequest):
    """400 Bad Request.

    A header is missing from the request.

    `header_name` is the only positional argument allowed,
    the other arguments are defined as keyword-only.

    Args:
        header_name (str): The name of the missing header.

    Keyword Args:
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        header_name: str,
        *,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ):
        description = 'The "{0}" header is required.'
        description = description.format(header_name)

        super().__init__(
            title='Missing header value',
            description=description,
            headers=headers,
            **kwargs,
        )


class HTTPInvalidParam(HTTPBadRequest):
    """400 Bad Request.

    A parameter in the request is invalid. This error may refer to a
    parameter in a query string, form, or document that was submitted
    with the request.

    `msg` and `param_name` are the only positional arguments allowed,
    the other arguments are defined as keyword-only.

    Args:
        msg (str): A description of the invalid parameter.
        param_name (str): The name of the parameter.

    Keyword Args:
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        msg: str,
        param_name: str,
        *,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ) -> None:
        description = 'The "{0}" parameter is invalid. {1}'
        description = description.format(param_name, msg)

        super().__init__(
            title='Invalid parameter',
            description=description,
            headers=headers,
            **kwargs,
        )


class HTTPMissingParam(HTTPBadRequest):
    """400 Bad Request.

    A parameter is missing from the request. This error may refer to a
    parameter in a query string, form, or document that was submitted
    with the request.

    `param_name` is the only positional argument allowed,
    the other arguments are defined as keyword-only.

    Args:
        param_name (str): The name of the missing parameter.

    Keyword Args:
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        param_name: str,
        *,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ) -> None:
        description = 'The "{0}" parameter is required.'
        description = description.format(param_name)

        super().__init__(
            title='Missing parameter',
            description=description,
            headers=headers,
            **kwargs,
        )


class MediaNotFoundError(HTTPBadRequest):
    """400 Bad Request.

    Exception raised by a media handler when trying to parse an empty body.

    Note:
        Some media handlers, like the one for URL-encoded forms, allow an
        empty body. In these cases this exception will not be raised.

    Args:
        media_type (str): The media type that was expected.

    Keyword Args:
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, media_type: str, **kwargs: HTTPErrorKeywordArguments) -> None:
        super().__init__(
            title='Invalid {0}'.format(media_type),
            description='Could not parse an empty {0} body'.format(media_type),
            **kwargs,  # type: ignore[arg-type]
        )


class MediaMalformedError(HTTPBadRequest):
    """400 Bad Request.

    Exception raised by a media handler when trying to parse a malformed body.
    The cause of this exception, if any, is stored in the ``__cause__`` attribute
    using the "raise ... from" form when raising.

    Args:
        media_type (str): The media type that was expected.

    Keyword Args:
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self, media_type: str, **kwargs: Union[HeaderArg, HTTPErrorKeywordArguments]
    ):
        super().__init__(
            title='Invalid {0}'.format(media_type),
            description=None,
            **kwargs,  # type: ignore[arg-type]
        )
        self._media_type = media_type

    @property
    def description(self) -> Optional[str]:
        msg = 'Could not parse {} body'.format(self._media_type)
        if self.__cause__ is not None:
            msg += ' - {}'.format(self.__cause__)
        return msg

    @description.setter
    def description(self, value: str) -> None:
        pass


class MediaValidationError(HTTPBadRequest):
    """400 Bad Request.

    Request media is invalid. This exception is raised by a media validator
    (such as
    :func:`jsonschema.validate <falcon.media.validators.jsonschema.validate>`)
    when ``req.media`` is successfully deserialized, but fails to validate
    against the configured schema.

    The cause of this exception, if any, is stored in the ``__cause__``
    attribute using the "raise ... from" form when raising.

    Note:
        All the arguments must be passed as keyword only.

    Keyword Args:
        title (str): Error title (default '400 Bad Request').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
        **kwargs: HTTPErrorKeywordArguments,
    ) -> None:
        super().__init__(
            title=title,
            description=description,
            headers=headers,
            **kwargs,
        )


class MultipartParseError(MediaMalformedError):
    """Represents a multipart form parsing error.

    This error may refer to a malformed or truncated form, usage of deprecated
    or unsupported features, or form parameters exceeding limits configured in
    :class:`~.media.multipart.MultipartParseOptions`.

    :class:`MultipartParseError` instances raised in this module always include
    a short human-readable description of the error.

    The cause of this exception, if any, is stored in the ``__cause__`` attribute
    using the "raise ... from" form when raising.

    Args:
        source_error (Exception): The source exception that was the cause of this one.
    """

    # NOTE(caselit): remove the description @property in MediaMalformedError
    description = None

    def __init__(
        self,
        *,
        description: Optional[str] = None,
        **kwargs: Union[HeaderArg, HTTPErrorKeywordArguments],
    ) -> None:
        HTTPBadRequest.__init__(
            self,
            title='Malformed multipart/form-data request media',
            description=description,
            **kwargs,  # type: ignore[arg-type]
        )


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _load_headers(headers: Optional[HeaderArg]) -> Headers:
    """Transform the headers to dict."""
    if headers is None:
        return {}
    if isinstance(headers, dict):
        return headers
    return dict(headers)


def _parse_retry_after(
    headers: Optional[HeaderArg],
    retry_after: RetryAfter,
) -> Optional[HeaderArg]:
    """Set the Retry-After to the headers when required."""
    if retry_after is None:
        return headers
    headers = _load_headers(headers)
    if isinstance(retry_after, datetime):
        headers['Retry-After'] = dt_to_http(retry_after)
    else:
        headers['Retry-After'] = str(retry_after)
    return headers
