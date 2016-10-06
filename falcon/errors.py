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

"""HTTP error classes.

This module implements a collection of `falcon.HTTPError`
specializations that can be raised to generate a 4xx or 5xx HTTP
response. All classes are available directly from the `falcon`
package namespace::

    import falcon

    class MessageResource(object):
        def on_get(self, req, resp):

            # ...

            raise falcon.HTTPBadRequest(
                'TTL Out of Range',
                'The message's TTL must be between 60 and 300 seconds, inclusive.'
            )

            # ...

"""

from datetime import datetime

from falcon import util
from falcon.http_error import HTTPError, NoRepresentation, \
    OptionalRepresentation
import falcon.status_codes as status


class HTTPBadRequest(HTTPError):
    """400 Bad Request.

    The server cannot or will not process the request due to something
    that is perceived to be a client error (e.g., malformed request
    syntax, invalid request message framing, or deceptive request
    routing).

    (See also: RFC 7231, Section 6.5.1)

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, title=None, description=None, **kwargs):
        super(HTTPBadRequest, self).__init__(status.HTTP_400, title,
                                             description, **kwargs)


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

    Keyword Args:
        title (str): Error title (default '401 Unauthorized').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        challenges (iterable of str): One or more authentication
            challenges to use as the value of the WWW-Authenticate header in
            the response (see also RFC 7235, Section 2.1).

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).

    """

    def __init__(self, title=None, description=None, challenges=None, **kwargs):
        headers = kwargs.setdefault('headers', {})

        if challenges:
            headers['WWW-Authenticate'] = ', '.join(challenges)

        super(HTTPUnauthorized, self).__init__(status.HTTP_401, title,
                                               description, **kwargs)


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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, title=None, description=None, **kwargs):
        super(HTTPForbidden, self).__init__(status.HTTP_403, title,
                                            description, **kwargs)


class HTTPNotFound(OptionalRepresentation, HTTPError):
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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, **kwargs):
        super(HTTPNotFound, self).__init__(status.HTTP_404, **kwargs)


class HTTPMethodNotAllowed(OptionalRepresentation, HTTPError):
    """405 Method Not Allowed.

    The method received in the request-line is known by the origin
    server but not supported by the target resource.

    The origin server MUST generate an Allow header field in a 405
    response containing a list of the target resource's currently
    supported methods.

    A 405 response is cacheable by default; i.e., unless otherwise
    indicated by the method definition or explicit cache controls.

    (See also: RFC 7231, Section 6.5.5)

    Args:
        allowed_methods (list of str): Allowed HTTP methods for this
            resource (e.g., ``['GET', 'POST', 'HEAD']``).

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, allowed_methods, **kwargs):
        new_headers = {'Allow': ', '.join(allowed_methods)}
        super(HTTPMethodNotAllowed, self).__init__(status.HTTP_405,
                                                   **kwargs)
        if not self.headers:
            self.headers = {}

        self.headers.update(new_headers)


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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, description=None, **kwargs):
        super(HTTPNotAcceptable, self).__init__(status.HTTP_406,
                                                'Media type not acceptable',
                                                description, **kwargs)


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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, title=None, description=None, **kwargs):
        super(HTTPConflict, self).__init__(status.HTTP_409, title,
                                           description, **kwargs)


class HTTPGone(OptionalRepresentation, HTTPError):
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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, **kwargs):
        super(HTTPGone, self).__init__(status.HTTP_410, **kwargs)


class HTTPLengthRequired(HTTPError):
    """411 Length Required.

    The server refuses to accept the request without a defined Content-
    Length.

    The client MAY repeat the request if it adds a valid Content-Length
    header field containing the length of the message body in the
    request message.

    (See also: RFC 7231, Section 6.5.10)

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """
    def __init__(self, title=None, description=None, **kwargs):
        super(HTTPLengthRequired, self).__init__(status.HTTP_411,
                                                 title, description, **kwargs)


class HTTPPreconditionFailed(HTTPError):
    """412 Precondition Failed.

    One or more conditions given in the request header fields evaluated
    to false when tested on the server.

    This response code allows the client to place preconditions on the
    current resource state (its current representations and metadata)
    and, thus, prevent the request method from being applied if the
    target resource is in an unexpected state.

    (See also: RFC 7232, Section 4.2)

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, title=None, description=None, **kwargs):
        super(HTTPPreconditionFailed, self).__init__(status.HTTP_412, title,
                                                     description, **kwargs)


class HTTPRequestEntityTooLarge(HTTPError):
    """413 Request Entity Too Large.

    The server is refusing to process a request because the request
    payload is larger than the server is willing or able to process.

    The server MAY close the connection to prevent the client from
    continuing the request.

    If the condition is temporary, the server SHOULD generate a Retry-
    After header field to indicate that it is temporary and after what
    time the client MAY try again.

    (See also: RFC 7231, Section 6.5.11)

    Keyword Args:
        title (str): Error title (default '413 Request Entity Too Large').

        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.

        retry_after (datetime or int): Value for the Retry-After
            header. If a ``datetime`` object, will serialize as an HTTP date.
            Otherwise, a non-negative ``int`` is expected, representing the
            number of seconds to wait.
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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, title=None, description=None, retry_after=None, **kwargs):
        headers = kwargs.setdefault('headers', {})

        if isinstance(retry_after, datetime):
            headers['Retry-After'] = util.dt_to_http(retry_after)
        elif retry_after is not None:
            headers['Retry-After'] = str(retry_after)

        super(HTTPRequestEntityTooLarge, self).__init__(status.HTTP_413,
                                                        title,
                                                        description,
                                                        **kwargs)


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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, title=None, description=None, **kwargs):
        super(HTTPUriTooLong, self).__init__(status.HTTP_414, title, description, **kwargs)


class HTTPUnsupportedMediaType(HTTPError):
    """415 Unsupported Media Type.

    The origin server is refusing to service the request because the
    payload is in a format not supported by this method on the target
    resource.

    The format problem might be due to the request's indicated Content-
    Type or Content-Encoding, or as a result of inspecting the data
    directly.

    (See also: RFC 7231, Section 6.5.13)

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, description=None, **kwargs):
        super(HTTPUnsupportedMediaType, self).__init__(
            status.HTTP_415, 'Unsupported media type', description, **kwargs)


class HTTPRangeNotSatisfiable(NoRepresentation, HTTPError):
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

    Args:
        resource_length: The maximum value for the last-byte-pos of a range
            request. Used to set the Content-Range header.
    """

    def __init__(self, resource_length):
        headers = {'Content-Range': 'bytes */' + str(resource_length)}
        super(HTTPRangeNotSatisfiable, self).__init__(status.HTTP_416,
                                                      headers=headers)


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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, title=None, description=None, **kwargs):
        super(HTTPUnprocessableEntity, self).__init__(status.HTTP_422, title,
                                                      description, **kwargs)


class HTTPTooManyRequests(HTTPError):
    """429 Too Many Requests.

    The user has sent too many requests in a given amount of time ("rate
    limiting").

    The response representations SHOULD include details explaining the
    condition, and MAY include a Retry-After header indicating how long
    to wait before making a new request.

    Responses with the 429 status code MUST NOT be stored by a cache.

    (See also: RFC 6585, Section 4)

    Keyword Args:
        title (str): Error title (default '429 Too Many Requests').
        description (str): Human-friendly description of the rate limit that
            was exceeded.
        retry_after (datetime or int): Value for the Retry-After
            header. If a ``datetime`` object, will serialize as an HTTP date.
            Otherwise, a non-negative ``int`` is expected, representing the
            number of seconds to wait.
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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, title=None, description=None, retry_after=None, **kwargs):
        headers = kwargs.setdefault('headers', {})

        if isinstance(retry_after, datetime):
            headers['Retry-After'] = util.dt_to_http(retry_after)
        elif retry_after is not None:
            headers['Retry-After'] = str(retry_after)

        super(HTTPTooManyRequests, self).__init__(status.HTTP_429,
                                                  title,
                                                  description,
                                                  **kwargs)


class HTTPUnavailableForLegalReasons(OptionalRepresentation, HTTPError):
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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, title=None, **kwargs):
        super(HTTPUnavailableForLegalReasons, self).__init__(status.HTTP_451,
                                                             title, **kwargs)


class HTTPInternalServerError(HTTPError):
    """500 Internal Server Error.

    The server encountered an unexpected condition that prevented it
    from fulfilling the request.

    (See also: RFC 7231, Section 6.6.1)

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).

    """

    def __init__(self, title=None, description=None, **kwargs):
        super(HTTPInternalServerError, self).__init__(status.HTTP_500, title,
                                                      description, **kwargs)


class HTTPBadGateway(HTTPError):
    """502 Bad Gateway.

    The server, while acting as a gateway or proxy, received an invalid
    response from an inbound server it accessed while attempting to
    fulfill the request.

    (See also: RFC 7231, Section 6.6.3)

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, title=None, description=None, **kwargs):
        super(HTTPBadGateway, self).__init__(status.HTTP_502, title,
                                             description, **kwargs)


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

    Keyword Args:
        title (str): Error title (default '503 Service Unavailable').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        retry_after (datetime or int): Value for the Retry-After header. If a
            ``datetime`` object, will serialize as an HTTP date. Otherwise,
            a non-negative ``int`` is expected, representing the number of
            seconds to wait.
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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, title=None, description=None, retry_after=None, **kwargs):
        headers = kwargs.setdefault('headers', {})

        if isinstance(retry_after, datetime):
            headers['Retry-After'] = util.dt_to_http(retry_after)
        elif retry_after is not None:
            headers['Retry-After'] = str(retry_after)

        super(HTTPServiceUnavailable, self).__init__(status.HTTP_503,
                                                     title,
                                                     description,
                                                     **kwargs)


class HTTPInvalidHeader(HTTPBadRequest):
    """400 Bad Request.

    One of the headers in the request is invalid.

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, msg, header_name, **kwargs):
        description = ('The value provided for the {0} header is '
                       'invalid. {1}')
        description = description.format(header_name, msg)

        super(HTTPInvalidHeader, self).__init__('Invalid header value',
                                                description, **kwargs)


class HTTPMissingHeader(HTTPBadRequest):
    """400 Bad Request

    A header is missing from the request.

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, header_name, **kwargs):
        description = 'The {0} header is required.'
        description = description.format(header_name)

        super(HTTPMissingHeader, self).__init__('Missing header value',
                                                description, **kwargs)


class HTTPInvalidParam(HTTPBadRequest):
    """400 Bad Request

    A parameter in the request is invalid. This error may refer to a
    parameter in a query string, form, or document that was submitted
    with the request.

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, msg, param_name, **kwargs):
        description = 'The "{0}" parameter is invalid. {1}'
        description = description.format(param_name, msg)

        super(HTTPInvalidParam, self).__init__('Invalid parameter',
                                               description, **kwargs)


class HTTPMissingParam(HTTPBadRequest):
    """400 Bad Request

    A parameter is missing from the request. This error may refer to a
    parameter in a query string, form, or document that was submitted
    with the request.

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

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    def __init__(self, param_name, **kwargs):
        description = 'The "{0}" parameter is required.'
        description = description.format(param_name)

        super(HTTPMissingParam, self).__init__('Missing parameter',
                                               description, **kwargs)
