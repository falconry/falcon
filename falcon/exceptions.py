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
from falcon.status_codes import *


class HTTPBadRequest(HTTPError):
    """400 Bad Request

    From RFC 2616:

    "The request could not be understood by the server due to malformed
    syntax. The client SHOULD NOT repeat the request without
    modifications."

    Args:
        Same as for HTTPError, exept status is set for you.

    """

    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_400, title, description, **kwargs)


class HTTPUnauthorized(HTTPError):
    """401 Unauthorized

    Use when authentication is required, and the provided credentials are
    not valid, or no credentials were provided in the first place.

    Args:
        title: Human-friendly error title
        description: Human-friendly description of the error, along with a
            helpful suggestion or two.
        scheme: Authentication scheme to use as the value of the
            WWW-Authenticate header in the response (default None).

    The remaining (optional) args are the same as for HTTPError.


    """

    def __init__(self, title, description, scheme=None, **kwargs):
        headers = kwargs.setdefault('headers', {})
        if scheme is not None:
            headers['WWW-Authenticate'] = scheme

        HTTPError.__init__(self, HTTP_401, title, description, **kwargs)


class HTTPForbidden(HTTPError):
    """403 Forbidden

    Use when the client's credentials are good, but they do not have permission
    to access the requested resource.

    Args:
        Same as for HTTPError, exept status is set for you.

    Note from RFC 2616:

    "If the request method was not HEAD and the server wishes to make
    public why the request has not been fulfilled, it SHOULD describe the
    reason for the refusal in the entity.  If the server does not wish to
    make this information available to the client, the status code 404
    (Not Found) can be used instead."

    """

    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_403, title, description, **kwargs)


class HTTPNotFound(HTTPError):
    """404 Not Found

    Use this when the URL path does not map to an existing resource, or you
    do not wish to disclose exactly why a request was refused.

    """
    def __init__(self):
        HTTPError.__init__(self, HTTP_404, None, None)


class HTTPMethodNotAllowed(HTTPError):
    """405 Method Not Allowed

    From RFC 2616:

    "The method specified in the Request-Line is not allowed for the
    resource identified by the Request-URI. The response MUST include an
    Allow header containing a list of valid methods for the requested
    resource."

    Args:
        allowed_methods: A list of allowed HTTP methods for this resource,
            such as ['GET', 'POST', 'HEAD'].

    The remaining (optional) args are the same as for HTTPError.

    """
    def __init__(self, allowed_methods, **kwargs):
        headers = kwargs.setdefault('headers', {})
        headers['Allow'] = ', '.join(allowed_methods)

        HTTPError.__init__(self, HTTP_405, None, **kwargs)


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

    Args:
        Same as for HTTPError, exept status is set for you.

    """
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_409, title, description, **kwargs)


class HTTPPreconditionFailed(HTTPError):
    """412 Precondition Failed

    From RFC 2616:

    "The precondition given in one or more of the request-header fields
    evaluated to false when it was tested on the server. This response
    code allows the client to place preconditions on the current resource
    metainformation (header field data) and thus prevent the requested
    method from being applied to a resource other than the one intended."

    Args:
        Same as for HTTPError, exept status is set for you.

    """
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_412, title, description, **kwargs)


class HTTPUnsupportedMediaType(HTTPError):
    """415 Unsupported Media Type

    Sets title to "Unsupported Media Type".

    Args:
        description: Human-friendly description of the error, along with a
            helpful suggestion or two.

    The remaining (optional) args are the same as for HTTPError.

    """
    def __init__(self, description, **kwargs):
        HTTPError.__init__(self, HTTP_415, 'Unsupported Media Type',
                           description, **kwargs)


class HTTPInternalServerError(HTTPError):
    """500 Internal Server Error

    Args:
        Same as for HTTPError, exept status is set for you.

    """
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_500, title, description, **kwargs)


class HTTPBadGateway(HTTPError):
    """502 Bad Gateway

    Args:
        Same as for HTTPError, exept status is set for you.

    """
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_502, title, description, **kwargs)


class HTTPServiceUnavailable(HTTPError):
    """503 Service Unavailable

    Args:
        Same as for HTTPError, exept status is set for you.

    """
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_503, title, description, **kwargs)
