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

from falcon.http_error import HTTPError, NoRepresentation
import falcon.status_codes as status


class HTTPBadRequest(HTTPError):
    """400 Bad Request.

    The request could not be understood by the server due to malformed
    syntax. The client SHOULD NOT repeat the request without
    modifications. (RFC 2616)

    Args:
        title (str): Error title (e.g., 'TTL Out of Range').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, status.HTTP_400, title, description, **kwargs)


class HTTPUnauthorized(HTTPError):
    """401 Unauthorized.

    Use when authentication is required, and the provided credentials are
    not valid, or no credentials were provided in the first place.

    Args:
        title (str): Error title (e.g., 'Authentication Required').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        scheme (str): Authentication scheme to use as the value of the
            WWW-Authenticate header in the response (default *None*).
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, title, description, **kwargs):
        headers = kwargs.setdefault('headers', {})

        scheme = kwargs.pop('scheme', None)
        if scheme is not None:
            headers['WWW-Authenticate'] = scheme

        HTTPError.__init__(self, status.HTTP_401, title, description, **kwargs)


class HTTPForbidden(HTTPError):
    """403 Forbidden.

    Use when the client's credentials are good, but they do not have permission
    to access the requested resource.

    If the request method was not HEAD and the server wishes to make
    public why the request has not been fulfilled, it SHOULD describe the
    reason for the refusal in the entity.  If the server does not wish to
    make this information available to the client, the status code 404
    (Not Found) can be used instead. (RFC 2616)

    Args:
        title (str): Error title (e.g., 'Permission Denied').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, status.HTTP_403, title, description, **kwargs)


class HTTPNotFound(NoRepresentation, HTTPError):
    """404 Not Found.

    Use this when the URL path does not map to an existing resource, or you
    do not wish to disclose exactly why a request was refused.

    """

    def __init__(self):
        HTTPError.__init__(self, status.HTTP_404)


class HTTPMethodNotAllowed(NoRepresentation, HTTPError):
    """405 Method Not Allowed.

    The method specified in the Request-Line is not allowed for the
    resource identified by the Request-URI. The response MUST include an
    Allow header containing a list of valid methods for the requested
    resource. (RFC 2616)

    Args:
        allowed_methods (list of str): Allowed HTTP methods for this
            resource (e.g., ['GET', 'POST', 'HEAD']).

    """

    def __init__(self, allowed_methods):
        headers = {'Allow': ', '.join(allowed_methods)}
        HTTPError.__init__(self, status.HTTP_405, headers=headers)


class HTTPNotAcceptable(HTTPError):
    """406 Not Acceptable.

    The client requested a resource in a representation that is not
    supported by the server. The client must indicate a supported
    media type in the Accept header.

    The resource identified by the request is only capable of generating
    response entities which have content characteristics not acceptable
    according to the accept headers sent in the request. (RFC 2616)

    Args:
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, description, **kwargs):
        HTTPError.__init__(self, status.HTTP_406, 'Media type not acceptable',
                           description, **kwargs)


class HTTPConflict(HTTPError):
    """409 Conflict.

    The request could not be completed due to a conflict with the current
    state of the resource. This code is only allowed in situations where
    it is expected that the user might be able to resolve the conflict
    and resubmit the request. The response body SHOULD include enough
    information for the user to recognize the source of the conflict.
    Ideally, the response entity would include enough information for the
    user or user agent to fix the problem; however, that might not be
    possible and is not required.

    Conflicts are most likely to occur in response to a PUT request. For
    example, if versioning were being used and the entity being PUT
    included changes to a resource which conflict with those made by an
    earlier (third-party) request, the server might use the 409 response
    to indicate that it can't complete the request. In this case, the
    response entity would likely contain a list of the differences
    between the two versions in a format defined by the response
    Content-Type.

    (RFC 2616)

    Args:
        title (str): Error title (e.g., 'Editing Conflict').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, status.HTTP_409, title, description, **kwargs)


class HTTPLengthRequired(HTTPError):
    """411 Length Required.

    The server refuses to accept the request without a defined
    Content-Length. The client MAY repeat the request if it adds a
    valid Content-Length header field containing the length of the
    message-body in the request message. (RFC 2616)

    Args:
        title (str): Error title (e.g., 'Missing Content-Length').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        kwargs (optional): Same as for ``HTTPError``.

    """
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, status.HTTP_411, title, description, **kwargs)


class HTTPPreconditionFailed(HTTPError):
    """412 Precondition Failed.

    The precondition given in one or more of the request-header fields
    evaluated to false when it was tested on the server. This response
    code allows the client to place preconditions on the current resource
    metainformation (header field data) and thus prevent the requested
    method from being applied to a resource other than the one intended.
    (RFC 2616)

    Args:
        title (str): Error title (e.g., 'Image Not Modified').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, status.HTTP_412, title, description, **kwargs)


class HTTPUnsupportedMediaType(HTTPError):
    """415 Unsupported Media Type.

    The client is trying to submit a resource encoded as an Internet media
    type that the server does not support.

    Args:
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, description, **kwargs):
        HTTPError.__init__(self, status.HTTP_415, 'Unsupported media type',
                           description, **kwargs)


class HTTPRangeNotSatisfiable(NoRepresentation, HTTPError):
    """416 Range Not Satisfiable.

    The requested range is not valid. See also: http://goo.gl/Qsa4EF

    Args:
        resource_length: The maximum value for the last-byte-pos of a range
            request. Used to set the Content-Range header.
    """

    def __init__(self, resource_length):
        headers = {'Content-Range': 'bytes */' + str(resource_length)}
        HTTPError.__init__(self, status.HTTP_416, headers=headers)


class HTTPInternalServerError(HTTPError):
    """500 Internal Server Error.

    Args:
        title (str): Error title (e.g., 'This Should Never Happen').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, status.HTTP_500, title, description, **kwargs)


class HTTPBadGateway(HTTPError):
    """502 Bad Gateway.

    Args:
        title (str): Error title, for
            example: 'Upstream Server is Unavailable'.
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, status.HTTP_502, title, description, **kwargs)


class HTTPServiceUnavailable(HTTPError):
    """503 Service Unavailable.

    Args:
        title (str): Error title (e.g., 'Temporarily Unavailable').
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two.
        retry_after (date or int): Value for the Retry-After header. If a date
            object, will serialize as an HTTP date. Otherwise, a non-negative
            int is expected, representing the number of seconds to wait. See
            also: http://goo.gl/DIrWr .
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, title, description, retry_after, **kwargs):
        headers = kwargs.setdefault('headers', {})
        headers['Retry-After'] = str(retry_after)
        HTTPError.__init__(self, status.HTTP_503, title, description, **kwargs)


class HTTPInvalidHeader(HTTPBadRequest):
    """HTTP header is invalid. Inherits from ``HTTPBadRequest``.

    Args:
        msg (str): A description of why the value is invalid.
        header_name (str): The name of the header.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, msg, header_name, **kwargs):
        description = ('The value provided for the {0} header is '
                       'invalid. {1}')
        description = description.format(header_name, msg)

        super(HTTPInvalidHeader, self).__init__('Invalid header value',
                                                description, **kwargs)


class HTTPMissingHeader(HTTPBadRequest):
    """HTTP header is missing. Inherits from ``HTTPBadRequest``.

    Args:
        header_name (str): The name of the header.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, header_name, **kwargs):
        description = ('The {0} header is required.')
        description = description.format(header_name)

        super(HTTPMissingHeader, self).__init__('Missing header value',
                                                description, **kwargs)


class HTTPInvalidParam(HTTPBadRequest):
    """HTTP parameter is invalid. Inherits from ``HTTPBadRequest``.

    Args:
        msg (str): A description of the invalid parameter.
        param_name (str): The name of the paramameter.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, msg, param_name, **kwargs):
        description = 'The "{0}" query parameter is invalid. {1}'
        description = description.format(param_name, msg)

        super(HTTPInvalidParam, self).__init__('Invalid query parameter',
                                               description, **kwargs)


class HTTPMissingParam(HTTPBadRequest):
    """HTTP parameter is missing. Inherits from ``HTTPBadRequest``.

    Args:
        param_name (str): The name of the paramameter.
        kwargs (optional): Same as for ``HTTPError``.

    """

    def __init__(self, param_name, **kwargs):
        description = 'The "{0}" query parameter is required.'
        description = description.format(param_name)

        super(HTTPMissingParam, self).__init__('Missing query parameter',
                                               description, **kwargs)
