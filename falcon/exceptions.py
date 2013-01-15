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

from .http_error import HTTPError
from .status_codes import *


# 400 Bad Request
class HTTPBadRequest(HTTPError):
    """400 Bad Request

    "The request could not be understood by the server due to malformed
    syntax. The client SHOULD NOT repeat the request without
    modifications." (RFC 2616)

    """

    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_400, title, description, **kwargs)


# 401 Unauthorized
class HTTPUnauthorized(HTTPError):
    """401 Unauthorized

    Use when authentication is required, and the provided credentials are
    not valid, or no credentials were provided in the first place.

    Args:
        scheme: Authentication scheme to use as the value of the
            WWW-Authenticate header in the response.
        title: Human-friendly error title
        description: Human-friendly description of the error, along with a
            helpful suggestion or two.

    The remaining (optional) args are the same as for HTTPError.


    """

    def __init__(self, scheme, title, description, **kwargs):
        headers = kwargs.setdefault('headers', {})
        headers['WWW-Authenticate'] = scheme
        HTTPError.__init__(self, HTTP_401, title, description, **kwargs)


# 403 Forbidden
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
        HTTPError.__init__(self, HTTP_403, title, description, **kwargs)


# 404 Not Found
class HTTPNotFound(HTTPError):
    """404 Not Found

    Use this when the URL path does not map to an existing resource, or you
    do not wish to disclose exactly why a request was refused.

    """
    def __init__(self):
        HTTPError.__init__(self, HTTP_404, None, None)


# 405 Method Not Allowed
class HTTPMethodNotAllowed(HTTPError):
    """A more readable version of HTTPError(HTTP_405, ...)"""
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_405, title, description, **kwargs)


# 412 Precondition Failed
class HTTPPreconditionFailed(HTTPError):
    """A more readable version of HTTPError(HTTP_412, ...)"""
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_412, title, description, **kwargs)


# 415 Unsupported Media Type
class HTTPUnsupportedMediaType(HTTPError):
    """A more readable version of HTTPError(HTTP_415, ...)"""
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_415, title, description, **kwargs)


# 409 Conflict
class HTTPConflict(HTTPError):
    """A more readable version of HTTPError(HTTP_409, ...)"""
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_409, title, description, **kwargs)


# 500 Internal Server Error
class HTTPInternalServerError(HTTPError):
    """A more readable version of HTTPError(HTTP_500, ...)"""
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_500, title, description, **kwargs)


# 502 Bad Gateway
class HTTPBadGateway(HTTPError):
    """A more readable version of HTTPError(HTTP_502, ...)"""
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_502, title, description, **kwargs)


# 503 Service Unavailable
class HTTPServiceUnavailable(HTTPError):
    """A more readable version of HTTPError(HTTP_503, ...)"""
    def __init__(self, title, description, **kwargs):
        HTTPError.__init__(self, HTTP_503, title, description, **kwargs)
