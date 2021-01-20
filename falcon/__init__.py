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

"""Primary package for Falcon, the minimalist web API framework.

Falcon is a minimalist web API framework for building speedy web APIs and app
backends. The `falcon` package can be used to directly access most of
the framework's classes, functions, and variables::

    import falcon

    app = falcon.App()

"""

import logging as _logging

# Hoist classes and functions into the falcon namespace
from falcon.app import API
from falcon.app import App
from falcon.constants import ASGI_SUPPORTED
from falcon.constants import COMBINED_METHODS
from falcon.constants import DEFAULT_MEDIA_TYPE
from falcon.constants import FALCON_CUSTOM_HTTP_METHODS
from falcon.constants import HTTP_METHODS
from falcon.constants import MEDIA_GIF
from falcon.constants import MEDIA_HTML
from falcon.constants import MEDIA_JPEG
from falcon.constants import MEDIA_JS
from falcon.constants import MEDIA_JSON
from falcon.constants import MEDIA_MSGPACK
from falcon.constants import MEDIA_MULTIPART
from falcon.constants import MEDIA_PNG
from falcon.constants import MEDIA_TEXT
from falcon.constants import MEDIA_URLENCODED
from falcon.constants import MEDIA_XML
from falcon.constants import MEDIA_YAML
from falcon.constants import PYPY
from falcon.constants import SINGLETON_HEADERS
from falcon.constants import WEBDAV_METHODS
from falcon.constants import WebSocketPayloadType
from falcon.errors import CompatibilityError
from falcon.errors import DelimiterError
from falcon.errors import HeaderNotSupported
from falcon.errors import HTTPBadGateway
from falcon.errors import HTTPBadRequest
from falcon.errors import HTTPConflict
from falcon.errors import HTTPFailedDependency
from falcon.errors import HTTPForbidden
from falcon.errors import HTTPGatewayTimeout
from falcon.errors import HTTPGone
from falcon.errors import HTTPInsufficientStorage
from falcon.errors import HTTPInternalServerError
from falcon.errors import HTTPInvalidHeader
from falcon.errors import HTTPInvalidParam
from falcon.errors import HTTPLengthRequired
from falcon.errors import HTTPLocked
from falcon.errors import HTTPLoopDetected
from falcon.errors import HTTPMethodNotAllowed
from falcon.errors import HTTPMissingHeader
from falcon.errors import HTTPMissingParam
from falcon.errors import HTTPNetworkAuthenticationRequired
from falcon.errors import HTTPNotAcceptable
from falcon.errors import HTTPNotFound
from falcon.errors import HTTPNotImplemented
from falcon.errors import HTTPPayloadTooLarge
from falcon.errors import HTTPPreconditionFailed
from falcon.errors import HTTPPreconditionRequired
from falcon.errors import HTTPRangeNotSatisfiable
from falcon.errors import HTTPRequestHeaderFieldsTooLarge
from falcon.errors import HTTPRouteNotFound
from falcon.errors import HTTPServiceUnavailable
from falcon.errors import HTTPTooManyRequests
from falcon.errors import HTTPUnauthorized
from falcon.errors import HTTPUnavailableForLegalReasons
from falcon.errors import HTTPUnprocessableEntity
from falcon.errors import HTTPUnsupportedMediaType
from falcon.errors import HTTPUriTooLong
from falcon.errors import HTTPVersionNotSupported
from falcon.errors import MediaMalformedError
from falcon.errors import MediaNotFoundError
from falcon.errors import OperationNotAllowed
from falcon.errors import PayloadTypeError
from falcon.errors import UnsupportedError
from falcon.errors import UnsupportedScopeError
from falcon.errors import WebSocketDisconnected
from falcon.errors import WebSocketHandlerNotFound
from falcon.errors import WebSocketPathNotFound
from falcon.errors import WebSocketServerError
from falcon.hooks import after
from falcon.hooks import before
from falcon.http_error import HTTPError
from falcon.http_status import HTTPStatus
from falcon.middleware import CORSMiddleware
from falcon.redirects import HTTPFound
from falcon.redirects import HTTPMovedPermanently
from falcon.redirects import HTTPPermanentRedirect
from falcon.redirects import HTTPSeeOther
from falcon.redirects import HTTPTemporaryRedirect
from falcon.request import Forwarded
from falcon.request import Request
from falcon.request import RequestOptions
from falcon.response import Response
from falcon.response import ResponseOptions
# Leave * for the status codes because they are too many to list all here.
from falcon.status_codes import *
from falcon.stream import BoundedStream
# NOTE(kgriffs): Ensure that "from falcon import uri" will import
# the same front-door module as "import falcon.uri". This works by
# priming the import cache with the one we want.
import falcon.uri
from falcon.util import async_to_sync
from falcon.util import BufferedReader
from falcon.util import CaseInsensitiveDict
from falcon.util import code_to_http_status
from falcon.util import Context
from falcon.util import create_task
from falcon.util import deprecated
from falcon.util import deprecation
from falcon.util import dt_to_http
from falcon.util import ETag
from falcon.util import get_argnames
from falcon.util import get_bound_method
from falcon.util import get_http_status
from falcon.util import get_running_loop
from falcon.util import http_cookies
from falcon.util import http_date_to_dt
from falcon.util import http_now
from falcon.util import http_status_to_code
from falcon.util import IS_64_BITS
from falcon.util import is_python_func
from falcon.util import misc
from falcon.util import reader
from falcon.util import runs_sync
from falcon.util import secure_filename
from falcon.util import structures
from falcon.util import sync
from falcon.util import sync_to_async
from falcon.util import sys
from falcon.util import time
from falcon.util import TimezoneGMT
from falcon.util import to_query_str
from falcon.util import uri
from falcon.util import wrap_sync_to_async
from falcon.util import wrap_sync_to_async_unsafe
from falcon.version import __version__


# NOTE(kgriffs): Only to be used internally on the rare occasion that we
#   need to log something that we can't communicate any other way.
_logger = _logging.getLogger('falcon')
_logger.addHandler(_logging.NullHandler())
