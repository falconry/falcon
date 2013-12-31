"""Defines exceptions for gracefully handling various HTTP errors.

Copyright 2013 by Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Class docstrings were copied from RFC 2616 where noted, and are not covered
by the above copyright.

"""

from falcon.http_error import HTTPError
import falcon.status_codes as status


class HTTPBadRequest(HTTPError):
    """400 Bad Request

    From RFC 2616:

    "The request could not be understood by the server due to malformed
    syntax. The client SHOULD NOT repeat the request without
    modifications."

    """

    def __init__(self, title, description, **kwargs):
        """Initialize

        Args:
            Same as for HTTPError, except status is set for you.

        """
        HTTPError.__init__(self, status.HTTP_400, title, description, **kwargs)


class HTTPUnauthorized(HTTPError):
    """401 Unauthorized

    Use when authentication is required, and the provided credentials are
    not valid, or no credentials were provided in the first place.

    """

    def __init__(self, title, description, **kwargs):
        """Initialize

        Args:
            title: Human-friendly error title
            description: Human-friendly description of the error, along with a
                helpful suggestion or two.
            scheme: Authentication scheme to use as the value of the
                WWW-Authenticate header in the response (default None).

        The remaining (optional) args are the same as for HTTPError.


        """
        headers = kwargs.setdefault('headers', {})

        scheme = kwargs.pop('scheme', None)
        if scheme is not None:
            headers['WWW-Authenticate'] = scheme

        HTTPError.__init__(self, status.HTTP_401, title, description, **kwargs)


class HTTPForbidden(HTTPError):
    """403 Forbidden

    Use when the client's credentials are good, but they do not have permission
    to access the requested resource.

    Note from RFC 2616:

    "If the request method was not HEAD and the server wishes to make
    public why the request has not been fulfilled, it SHOULD describe the
    reason for the refusal in the entity.  If the server does not wish to
    make this information available to the client, the status code 404
    (Not Found) can be used instead."

    """

    def __init__(self, title, description, **kwargs):
        """Initialize

        Args:
            Same as for HTTPError, except status is set for you.

        """

        HTTPError.__init__(self, status.HTTP_403, title, description, **kwargs)


class HTTPNotFound(HTTPError):
    """404 Not Found

    Use this when the URL path does not map to an existing resource, or you
    do not wish to disclose exactly why a request was refused.

    """
    def __init__(self):
        """Initialize"""

        HTTPError.__init__(self, status.HTTP_404, None, None)


class HTTPMethodNotAllowed(HTTPError):
    """405 Method Not Allowed

    From RFC 2616:

    "The method specified in the Request-Line is not allowed for the
    resource identified by the Request-URI. The response MUST include an
    Allow header containing a list of valid methods for the requested
    resource."

    """
    def __init__(self, allowed_methods, **kwargs):
        """Initilize with allowed methods

        Args:
            allowed_methods: A list of allowed HTTP methods for this resource,
                such as ['GET', 'POST', 'HEAD'].

        The remaining (optional) args are the same as for HTTPError.

        """
        headers = kwargs.setdefault('headers', {})
        headers['Allow'] = ', '.join(allowed_methods)

        HTTPError.__init__(self, status.HTTP_405, None, **kwargs)


class HTTPNotAcceptable(HTTPError):
    """406 Not Acceptable

    Use this to reject the clients without a specific media type
    support in their Accept headers.

    From RFC 2616:

    "The resource identified by the request is only capable of generating
    response entities which have content characteristics not acceptable
    according to the accept headers sent in the request."

    """
    def __init__(self, description, **kwargs):
        """Initialize

        Args:
            description: Human-friendly description of the error, along with a
                helpful suggestion or two.

        The remaining (optional) args are the same as for HTTPError.

        """

        HTTPError.__init__(self, status.HTTP_406, 'Media type not acceptable',
                           description, **kwargs)


class HTTPConflict(HTTPError):
    """409 Conflict

    From RFC 2616:

    "The request could not be completed due to a conflict with the current
    state of the resource. This code is only allowed in situations where
    it is expected that the user might be able to resolve the conflict
    and resubmit the request. The response body SHOULD include enough
    information for the user to recognize the source of the conflict.
    Ideally, the response entity would include enough information for the
    user or user agent to fix the problem; however, that might not be
    possible and is not required."

    "Conflicts are most likely to occur in response to a PUT request. For
    example, if versioning were being used and the entity being PUT
    included changes to a resource which conflict with those made by an
    earlier (third-party) request, the server might use the 409 response
    to indicate that it can't complete the request. In this case, the
    response entity would likely contain a list of the differences
    between the two versions in a format defined by the response
    Content-Type."

    """

    def __init__(self, title, description, **kwargs):
        """Initialize

        Args:
            Same as for HTTPError, except status is set for you.

        """

        HTTPError.__init__(self, status.HTTP_409, title, description, **kwargs)


class HTTPLengthRequired(HTTPError):
    """411 Length Required

    From RFC 2616:

    "The server refuses to accept the request without a defined
   Content- Length. The client MAY repeat the request if it adds a
   valid Content-Length header field containing the length of the
   message-body in the request message."

    """
    def __init__(self, title, description, **kwargs):
        """Initialize

        Args:
            Same as for HTTPError, except status is set for you.

        """
        HTTPError.__init__(self, status.HTTP_411, title, description, **kwargs)


class HTTPPreconditionFailed(HTTPError):
    """412 Precondition Failed

    From RFC 2616:

    "The precondition given in one or more of the request-header fields
    evaluated to false when it was tested on the server. This response
    code allows the client to place preconditions on the current resource
    metainformation (header field data) and thus prevent the requested
    method from being applied to a resource other than the one intended."

    """

    def __init__(self, title, description, **kwargs):
        """Initialize

        Args:
            Same as for HTTPError, except status is set for you.

        """

        HTTPError.__init__(self, status.HTTP_412, title, description, **kwargs)


class HTTPUnsupportedMediaType(HTTPError):
    """415 Unsupported Media Type

    Sets title to "Unsupported media type".

    """

    def __init__(self, description, **kwargs):
        """Initialize

        Args:
            description: Human-friendly description of the error, along with a
                helpful suggestion or two.

        The remaining (optional) args are the same as for HTTPError.

        """

        HTTPError.__init__(self, status.HTTP_415, 'Unsupported media type',
                           description, **kwargs)


class HTTPRangeNotSatisfiable(HTTPError):
    """416 Range Not Satisfiable

    See also: http://goo.gl/yvh9H

    Args:
        resource_length: The maximum value for the last-byte-pos of a range
            request. Used to set the Content-Range header.
        media_type: Media type to use as the value of the Content-Type
            header, or None to use the default passed to the API initializer.

    """

    def __init__(self, resource_length, media_type=None):
        """Initialize

        Args:
            resource_length: The maximum value for the last-byte-pos of a
                range request. Used to set the Content-Range header.
            media_type: Media type to use as the value of the Content-Type
                header, or None to use the default passed to the API
                initializer.

        """

        headers = {'Content-Range': 'bytes */' + str(resource_length)}
        if media_type is not None:
            headers['Content-Type'] = media_type

        HTTPError.__init__(self, status.HTTP_416, None, None, headers=headers)


class HTTPUpgradeRequired(HTTPError):
    """426 Upgrade Required"""

    def __init__(self, title, description, **kwargs):
        """Initialize

        Args:
            Same as for HTTPError, except status is set for you.

        """

        HTTPError.__init__(self, status.HTTP_426, title, description, **kwargs)


class HTTPInternalServerError(HTTPError):
    """500 Internal Server Error"""

    def __init__(self, title, description, **kwargs):
        """Initialize

        Args:
            Same as for HTTPError, except status is set for you.

        """

        HTTPError.__init__(self, status.HTTP_500, title, description, **kwargs)


class HTTPBadGateway(HTTPError):
    """502 Bad Gateway"""

    def __init__(self, title, description, **kwargs):
        """Initialize

        Args:
            Same as for HTTPError, except status is set for you.

        """

        HTTPError.__init__(self, status.HTTP_502, title, description, **kwargs)


class HTTPServiceUnavailable(HTTPError):
    """503 Service Unavailable"""

    def __init__(self, title, description, retry_after, **kwargs):
        """Initialize

        Args:
            title: Human-friendly error title. Set to None if you wish Falcon
                to return an empty response body (all remaining args will
                be ignored except for headers.) Do this only when you don't
                wish to disclose sensitive information about why a request was
                refused, or if the status and headers are self-descriptive.
            description: Human-friendly description of the error, along with a
                helpful suggestion or two (default None).
            retry_after: Value for the Retry-After header. If a date object,
                will serialize as an HTTP date. Otherwise, a non-negative int
                is expected, representing the number of seconds to wait. See
                also: http://goo.gl/DIrWr
            headers: A dictionary of extra headers to return in the
                response to the client (default None).
            href: A URL someone can visit to find out more information
                (default None).
            href_rel: If href is given, use this value for the rel
                attribute (default 'doc').
            href_text: If href is given, use this as the friendly
                title/description for the link (defaults to "API documentation
                for this error").
            code: An internal code that customers can reference in their
                support request or to help them when searching for knowledge
                base articles related to this error.
        """

        headers = kwargs.setdefault('headers', {})
        headers['Retry-After'] = str(retry_after)
        HTTPError.__init__(self, status.HTTP_503, title, description, **kwargs)
