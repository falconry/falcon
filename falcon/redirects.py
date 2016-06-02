# Copyright 2015 by Kurt Griffiths
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

"""HTTPStatus specializations for 3xx redirects."""

import falcon
from falcon.http_status import HTTPStatus


class HTTPMovedPermanently(HTTPStatus):
    """301 Moved Permanently.

    The 301 (Moved Permanently) status code indicates that the target
    resource has been assigned a new permanent URI.

    Note:
        For historical reasons, a user agent MAY change the request
        method from POST to GET for the subsequent request.  If this
        behavior is undesired, the 308 (Permanent Redirect) status code
        can be used instead.

    See also: https://tools.ietf.org/html/rfc7231#section-6.4.2

    Args:
        location (str): URI to provide as the Location header in the
            response.
    """

    def __init__(self, location):
        super(HTTPMovedPermanently, self).__init__(
            falcon.HTTP_301, {'location': location})


class HTTPFound(HTTPStatus):
    """302 Found.

    The 302 (Found) status code indicates that the target resource
    resides temporarily under a different URI.  Since the redirection
    might be altered on occasion, the client ought to continue to use the
    effective request URI for future requests.

    Note:
        For historical reasons, a user agent MAY change the request
        method from POST to GET for the subsequent request.  If this
        behavior is undesired, the 307 (Temporary Redirect) status code
        can be used instead.

    See also: https://tools.ietf.org/html/rfc7231#section-6.4.3

    Args:
        location (str): URI to provide as the Location header in the
            response.
    """

    def __init__(self, location):
        super(HTTPFound, self).__init__(
            falcon.HTTP_302, {'location': location})


class HTTPSeeOther(HTTPStatus):
    """303 See Other.

    The 303 (See Other) status code indicates that the server is
    redirecting the user agent to a *different* resource, as indicated
    by a URI in the Location header field, which is intended to provide
    an indirect response to the original request.

    A 303 response to a GET request indicates that the origin server
    does not have a representation of the target resource that can be
    transferred over HTTP. However, the Location header in the response
    may be dereferenced to obtain a representation for an alternative
    resource. The recipient may find this alternative useful, even
    though it does not represent the original target resource.

    Note:
        The new URI in the Location header field is not considered
        equivalent to the effective request URI.

    See also: https://tools.ietf.org/html/rfc7231#section-6.4.4

    Args:
        location (str): URI to provide as the Location header in the
            response.
    """

    def __init__(self, location):
        super(HTTPSeeOther, self).__init__(
            falcon.HTTP_303, {'location': location})


class HTTPTemporaryRedirect(HTTPStatus):
    """307 Temporary Redirect.

    The 307 (Temporary Redirect) status code indicates that the target
    resource resides temporarily under a different URI and the user
    agent MUST NOT change the request method if it performs an automatic
    redirection to that URI.  Since the redirection can change over
    time, the client ought to continue using the original effective
    request URI for future requests.

    Note:
        This status code is similar to 302 (Found), except that it
        does not allow changing the request method from POST to GET.

    See also: https://tools.ietf.org/html/rfc7231#section-6.4.7

    Args:
        location (str): URI to provide as the Location header in the
            response.
    """

    def __init__(self, location):
        super(HTTPTemporaryRedirect, self).__init__(
            falcon.HTTP_307, {'location': location})


class HTTPPermanentRedirect(HTTPStatus):
    """308 Permanent Redirect.

    The 308 (Permanent Redirect) status code indicates that the target
    resource has been assigned a new permanent URI.

    Note:
        This status code is similar to 301 (Moved Permanently), except
        that it does not allow changing the request method from POST to
        GET.

    See also: https://tools.ietf.org/html/rfc7238#section-3

    Args:
        location (str): URI to provide as the Location header in the
            response.
    """

    def __init__(self, location):
        super(HTTPPermanentRedirect, self).__init__(
            falcon.HTTP_308, {'location': location})
