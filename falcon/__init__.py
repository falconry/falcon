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

__all__ = (
    # API interface
    'API',
    'App',
    'after',
    'before',
    'BoundedStream',
    'CORSMiddleware',
    'HTTPError',
    'HTTPStatus',
    'HTTPFound',
    'HTTPMovedPermanently',
    'HTTPPermanentRedirect',
    'HTTPSeeOther',
    'HTTPTemporaryRedirect',
    'Forwarded',
    'Request',
    'RequestOptions',
    'Response',
    'ResponseOptions',
    # Public constants
    'HTTP_METHODS',
    'WEBDAV_METHODS',
    'COMBINED_METHODS',
    'DEFAULT_MEDIA_TYPE',
    'MEDIA_BMP',
    'MEDIA_GIF',
    'MEDIA_HTML',
    'MEDIA_JPEG',
    'MEDIA_JS',
    'MEDIA_JSON',
    'MEDIA_MSGPACK',
    'MEDIA_MULTIPART',
    'MEDIA_PNG',
    'MEDIA_TEXT',
    'MEDIA_URLENCODED',
    'MEDIA_XML',
    'MEDIA_YAML',
    'SINGLETON_HEADERS',
    'WebSocketPayloadType',
    # Utilities
    'async_to_sync',
    'BufferedReader',
    'CaseInsensitiveDict',
    'code_to_http_status',
    'Context',
    'create_task',
    'deprecated',
    'dt_to_http',
    'ETag',
    'get_argnames',
    'get_bound_method',
    'get_running_loop',
    'http_cookies',
    'http_date_to_dt',
    'http_now',
    'http_status_to_code',
    'IS_64_BITS',
    'is_python_func',
    'mediatypes',
    'misc',
    'parse_header',
    'reader',
    'runs_sync',
    'secure_filename',
    'structures',
    'sync',
    'sync_to_async',
    'time',
    'TimezoneGMT',
    'to_query_str',
    'uri',
    'wrap_sync_to_async',
    'wrap_sync_to_async_unsafe',
    # Error classes
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
    'HTTPPayloadTooLarge',
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
    # HTTP status codes
    'HTTP_100',
    'HTTP_101',
    'HTTP_102',
    'HTTP_103',
    'HTTP_200',
    'HTTP_201',
    'HTTP_202',
    'HTTP_203',
    'HTTP_204',
    'HTTP_205',
    'HTTP_206',
    'HTTP_207',
    'HTTP_208',
    'HTTP_226',
    'HTTP_300',
    'HTTP_301',
    'HTTP_302',
    'HTTP_303',
    'HTTP_304',
    'HTTP_305',
    'HTTP_307',
    'HTTP_308',
    'HTTP_400',
    'HTTP_401',
    'HTTP_402',
    'HTTP_403',
    'HTTP_404',
    'HTTP_405',
    'HTTP_406',
    'HTTP_407',
    'HTTP_408',
    'HTTP_409',
    'HTTP_410',
    'HTTP_411',
    'HTTP_412',
    'HTTP_413',
    'HTTP_414',
    'HTTP_415',
    'HTTP_416',
    'HTTP_417',
    'HTTP_418',
    'HTTP_421',
    'HTTP_422',
    'HTTP_423',
    'HTTP_424',
    'HTTP_425',
    'HTTP_426',
    'HTTP_428',
    'HTTP_429',
    'HTTP_431',
    'HTTP_451',
    'HTTP_500',
    'HTTP_501',
    'HTTP_502',
    'HTTP_503',
    'HTTP_504',
    'HTTP_505',
    'HTTP_506',
    'HTTP_507',
    'HTTP_508',
    'HTTP_510',
    'HTTP_511',
    'HTTP_701',
    'HTTP_702',
    'HTTP_703',
    'HTTP_710',
    'HTTP_711',
    'HTTP_712',
    'HTTP_719',
    'HTTP_720',
    'HTTP_721',
    'HTTP_722',
    'HTTP_723',
    'HTTP_724',
    'HTTP_725',
    'HTTP_726',
    'HTTP_727',
    'HTTP_740',
    'HTTP_741',
    'HTTP_742',
    'HTTP_743',
    'HTTP_744',
    'HTTP_745',
    'HTTP_748',
    'HTTP_749',
    'HTTP_750',
    'HTTP_753',
    'HTTP_754',
    'HTTP_755',
    'HTTP_759',
    'HTTP_771',
    'HTTP_772',
    'HTTP_773',
    'HTTP_774',
    'HTTP_776',
    'HTTP_777',
    'HTTP_778',
    'HTTP_779',
    'HTTP_780',
    'HTTP_781',
    'HTTP_782',
    'HTTP_783',
    'HTTP_784',
    'HTTP_785',
    'HTTP_786',
    'HTTP_791',
    'HTTP_792',
    'HTTP_797',
    'HTTP_799',
    'HTTP_ACCEPTED',
    'HTTP_ALREADY_REPORTED',
    'HTTP_BAD_GATEWAY',
    'HTTP_BAD_REQUEST',
    'HTTP_CONFLICT',
    'HTTP_CONTENT_TOO_LARGE',
    'HTTP_CONTINUE',
    'HTTP_CREATED',
    'HTTP_EARLY_HINTS',
    'HTTP_EXPECTATION_FAILED',
    'HTTP_FAILED_DEPENDENCY',
    'HTTP_FORBIDDEN',
    'HTTP_FOUND',
    'HTTP_GATEWAY_TIMEOUT',
    'HTTP_GONE',
    'HTTP_HTTP_VERSION_NOT_SUPPORTED',
    'HTTP_IM_A_TEAPOT',
    'HTTP_IM_USED',
    'HTTP_INSUFFICIENT_STORAGE',
    'HTTP_INTERNAL_SERVER_ERROR',
    'HTTP_LENGTH_REQUIRED',
    'HTTP_LOCKED',
    'HTTP_LOOP_DETECTED',
    'HTTP_METHOD_NOT_ALLOWED',
    'HTTP_MISDIRECTED_REQUEST',
    'HTTP_MOVED_PERMANENTLY',
    'HTTP_MULTIPLE_CHOICES',
    'HTTP_MULTI_STATUS',
    'HTTP_NETWORK_AUTHENTICATION_REQUIRED',
    'HTTP_NON_AUTHORITATIVE_INFORMATION',
    'HTTP_NOT_ACCEPTABLE',
    'HTTP_NOT_EXTENDED',
    'HTTP_NOT_FOUND',
    'HTTP_NOT_IMPLEMENTED',
    'HTTP_NOT_MODIFIED',
    'HTTP_NO_CONTENT',
    'HTTP_OK',
    'HTTP_PARTIAL_CONTENT',
    'HTTP_PAYMENT_REQUIRED',
    'HTTP_PERMANENT_REDIRECT',
    'HTTP_PRECONDITION_FAILED',
    'HTTP_PRECONDITION_REQUIRED',
    'HTTP_PROCESSING',
    'HTTP_PROXY_AUTHENTICATION_REQUIRED',
    'HTTP_REQUESTED_RANGE_NOT_SATISFIABLE',
    'HTTP_REQUEST_HEADER_FIELDS_TOO_LARGE',
    'HTTP_REQUEST_TIMEOUT',
    'HTTP_REQUEST_URI_TOO_LONG',
    'HTTP_RESET_CONTENT',
    'HTTP_SEE_OTHER',
    'HTTP_SERVICE_UNAVAILABLE',
    'HTTP_SWITCHING_PROTOCOLS',
    'HTTP_TEMPORARY_REDIRECT',
    'HTTP_TOO_EARLY',
    'HTTP_TOO_MANY_REQUESTS',
    'HTTP_UNAUTHORIZED',
    'HTTP_UNAVAILABLE_FOR_LEGAL_REASONS',
    'HTTP_UNPROCESSABLE_ENTITY',
    'HTTP_UNSUPPORTED_MEDIA_TYPE',
    'HTTP_UPGRADE_REQUIRED',
    'HTTP_USE_PROXY',
    'HTTP_VARIANT_ALSO_NEGOTIATES',
)

# NOTE(kgriffs,vytas): Hoist classes and functions into the falcon namespace.
#   Please explicitly list ALL exports.
from falcon.app import API
from falcon.app import App
from falcon.constants import ASGI_SUPPORTED  # NOQA: F401
from falcon.constants import COMBINED_METHODS
from falcon.constants import DEFAULT_MEDIA_TYPE
from falcon.constants import HTTP_METHODS
from falcon.constants import MEDIA_BMP
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
from falcon.constants import PYTHON_VERSION  # NOQA: F401
from falcon.constants import SINGLETON_HEADERS
from falcon.constants import WEBDAV_METHODS
from falcon.constants import WebSocketPayloadType
from falcon.errors import CompatibilityError
from falcon.errors import DelimiterError
from falcon.errors import HeaderNotSupported
from falcon.errors import HTTPBadGateway
from falcon.errors import HTTPBadRequest
from falcon.errors import HTTPConflict
from falcon.errors import HTTPContentTooLarge
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
from falcon.errors import InvalidMediaRange
from falcon.errors import InvalidMediaType
from falcon.errors import MediaMalformedError
from falcon.errors import MediaNotFoundError
from falcon.errors import MediaValidationError
from falcon.errors import MultipartParseError
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

# Hoist HTTP status codes.
from falcon.status_codes import HTTP_100
from falcon.status_codes import HTTP_101
from falcon.status_codes import HTTP_102
from falcon.status_codes import HTTP_103
from falcon.status_codes import HTTP_200
from falcon.status_codes import HTTP_201
from falcon.status_codes import HTTP_202
from falcon.status_codes import HTTP_203
from falcon.status_codes import HTTP_204
from falcon.status_codes import HTTP_205
from falcon.status_codes import HTTP_206
from falcon.status_codes import HTTP_207
from falcon.status_codes import HTTP_208
from falcon.status_codes import HTTP_226
from falcon.status_codes import HTTP_300
from falcon.status_codes import HTTP_301
from falcon.status_codes import HTTP_302
from falcon.status_codes import HTTP_303
from falcon.status_codes import HTTP_304
from falcon.status_codes import HTTP_305
from falcon.status_codes import HTTP_307
from falcon.status_codes import HTTP_308
from falcon.status_codes import HTTP_400
from falcon.status_codes import HTTP_401
from falcon.status_codes import HTTP_402
from falcon.status_codes import HTTP_403
from falcon.status_codes import HTTP_404
from falcon.status_codes import HTTP_405
from falcon.status_codes import HTTP_406
from falcon.status_codes import HTTP_407
from falcon.status_codes import HTTP_408
from falcon.status_codes import HTTP_409
from falcon.status_codes import HTTP_410
from falcon.status_codes import HTTP_411
from falcon.status_codes import HTTP_412
from falcon.status_codes import HTTP_413
from falcon.status_codes import HTTP_414
from falcon.status_codes import HTTP_415
from falcon.status_codes import HTTP_416
from falcon.status_codes import HTTP_417
from falcon.status_codes import HTTP_418
from falcon.status_codes import HTTP_421
from falcon.status_codes import HTTP_422
from falcon.status_codes import HTTP_423
from falcon.status_codes import HTTP_424
from falcon.status_codes import HTTP_425
from falcon.status_codes import HTTP_426
from falcon.status_codes import HTTP_428
from falcon.status_codes import HTTP_429
from falcon.status_codes import HTTP_431
from falcon.status_codes import HTTP_451
from falcon.status_codes import HTTP_500
from falcon.status_codes import HTTP_501
from falcon.status_codes import HTTP_502
from falcon.status_codes import HTTP_503
from falcon.status_codes import HTTP_504
from falcon.status_codes import HTTP_505
from falcon.status_codes import HTTP_506
from falcon.status_codes import HTTP_507
from falcon.status_codes import HTTP_508
from falcon.status_codes import HTTP_510
from falcon.status_codes import HTTP_511
from falcon.status_codes import HTTP_701
from falcon.status_codes import HTTP_702
from falcon.status_codes import HTTP_703
from falcon.status_codes import HTTP_710
from falcon.status_codes import HTTP_711
from falcon.status_codes import HTTP_712
from falcon.status_codes import HTTP_719
from falcon.status_codes import HTTP_720
from falcon.status_codes import HTTP_721
from falcon.status_codes import HTTP_722
from falcon.status_codes import HTTP_723
from falcon.status_codes import HTTP_724
from falcon.status_codes import HTTP_725
from falcon.status_codes import HTTP_726
from falcon.status_codes import HTTP_727
from falcon.status_codes import HTTP_740
from falcon.status_codes import HTTP_741
from falcon.status_codes import HTTP_742
from falcon.status_codes import HTTP_743
from falcon.status_codes import HTTP_744
from falcon.status_codes import HTTP_745
from falcon.status_codes import HTTP_748
from falcon.status_codes import HTTP_749
from falcon.status_codes import HTTP_750
from falcon.status_codes import HTTP_753
from falcon.status_codes import HTTP_754
from falcon.status_codes import HTTP_755
from falcon.status_codes import HTTP_759
from falcon.status_codes import HTTP_771
from falcon.status_codes import HTTP_772
from falcon.status_codes import HTTP_773
from falcon.status_codes import HTTP_774
from falcon.status_codes import HTTP_776
from falcon.status_codes import HTTP_777
from falcon.status_codes import HTTP_778
from falcon.status_codes import HTTP_779
from falcon.status_codes import HTTP_780
from falcon.status_codes import HTTP_781
from falcon.status_codes import HTTP_782
from falcon.status_codes import HTTP_783
from falcon.status_codes import HTTP_784
from falcon.status_codes import HTTP_785
from falcon.status_codes import HTTP_786
from falcon.status_codes import HTTP_791
from falcon.status_codes import HTTP_792
from falcon.status_codes import HTTP_797
from falcon.status_codes import HTTP_799
from falcon.status_codes import HTTP_ACCEPTED
from falcon.status_codes import HTTP_ALREADY_REPORTED
from falcon.status_codes import HTTP_BAD_GATEWAY
from falcon.status_codes import HTTP_BAD_REQUEST
from falcon.status_codes import HTTP_CONFLICT
from falcon.status_codes import HTTP_CONTENT_TOO_LARGE
from falcon.status_codes import HTTP_CONTINUE
from falcon.status_codes import HTTP_CREATED
from falcon.status_codes import HTTP_EARLY_HINTS
from falcon.status_codes import HTTP_EXPECTATION_FAILED
from falcon.status_codes import HTTP_FAILED_DEPENDENCY
from falcon.status_codes import HTTP_FORBIDDEN
from falcon.status_codes import HTTP_FOUND
from falcon.status_codes import HTTP_GATEWAY_TIMEOUT
from falcon.status_codes import HTTP_GONE
from falcon.status_codes import HTTP_HTTP_VERSION_NOT_SUPPORTED
from falcon.status_codes import HTTP_IM_A_TEAPOT
from falcon.status_codes import HTTP_IM_USED
from falcon.status_codes import HTTP_INSUFFICIENT_STORAGE
from falcon.status_codes import HTTP_INTERNAL_SERVER_ERROR
from falcon.status_codes import HTTP_LENGTH_REQUIRED
from falcon.status_codes import HTTP_LOCKED
from falcon.status_codes import HTTP_LOOP_DETECTED
from falcon.status_codes import HTTP_METHOD_NOT_ALLOWED
from falcon.status_codes import HTTP_MISDIRECTED_REQUEST
from falcon.status_codes import HTTP_MOVED_PERMANENTLY
from falcon.status_codes import HTTP_MULTI_STATUS
from falcon.status_codes import HTTP_MULTIPLE_CHOICES
from falcon.status_codes import HTTP_NETWORK_AUTHENTICATION_REQUIRED
from falcon.status_codes import HTTP_NO_CONTENT
from falcon.status_codes import HTTP_NON_AUTHORITATIVE_INFORMATION
from falcon.status_codes import HTTP_NOT_ACCEPTABLE
from falcon.status_codes import HTTP_NOT_EXTENDED
from falcon.status_codes import HTTP_NOT_FOUND
from falcon.status_codes import HTTP_NOT_IMPLEMENTED
from falcon.status_codes import HTTP_NOT_MODIFIED
from falcon.status_codes import HTTP_OK
from falcon.status_codes import HTTP_PARTIAL_CONTENT
from falcon.status_codes import HTTP_PAYMENT_REQUIRED
from falcon.status_codes import HTTP_PERMANENT_REDIRECT
from falcon.status_codes import HTTP_PRECONDITION_FAILED
from falcon.status_codes import HTTP_PRECONDITION_REQUIRED
from falcon.status_codes import HTTP_PROCESSING
from falcon.status_codes import HTTP_PROXY_AUTHENTICATION_REQUIRED
from falcon.status_codes import HTTP_REQUEST_HEADER_FIELDS_TOO_LARGE
from falcon.status_codes import HTTP_REQUEST_TIMEOUT
from falcon.status_codes import HTTP_REQUEST_URI_TOO_LONG
from falcon.status_codes import HTTP_REQUESTED_RANGE_NOT_SATISFIABLE
from falcon.status_codes import HTTP_RESET_CONTENT
from falcon.status_codes import HTTP_SEE_OTHER
from falcon.status_codes import HTTP_SERVICE_UNAVAILABLE
from falcon.status_codes import HTTP_SWITCHING_PROTOCOLS
from falcon.status_codes import HTTP_TEMPORARY_REDIRECT
from falcon.status_codes import HTTP_TOO_EARLY
from falcon.status_codes import HTTP_TOO_MANY_REQUESTS
from falcon.status_codes import HTTP_UNAUTHORIZED
from falcon.status_codes import HTTP_UNAVAILABLE_FOR_LEGAL_REASONS
from falcon.status_codes import HTTP_UNPROCESSABLE_ENTITY
from falcon.status_codes import HTTP_UNSUPPORTED_MEDIA_TYPE
from falcon.status_codes import HTTP_UPGRADE_REQUIRED
from falcon.status_codes import HTTP_USE_PROXY
from falcon.status_codes import HTTP_VARIANT_ALSO_NEGOTIATES
from falcon.stream import BoundedStream

# NOTE(kgriffs): Ensure that "from falcon import uri" will import
#   the same front-door module as "import falcon.uri". This works by
#   priming the import cache with the one we want.
import falcon.uri  # NOQA: F401

# Hoist utilities.
from falcon.util import async_to_sync
from falcon.util import BufferedReader
from falcon.util import CaseInsensitiveDict
from falcon.util import code_to_http_status
from falcon.util import Context
from falcon.util import create_task

# NOTE(kgriffs): Hosting only because this was previously referenced
#   in the docs as falcon.deprecated
from falcon.util import deprecated
from falcon.util import dt_to_http
from falcon.util import ETag
from falcon.util import get_argnames
from falcon.util import get_bound_method
from falcon.util import get_running_loop
from falcon.util import http_cookies
from falcon.util import http_date_to_dt
from falcon.util import http_now
from falcon.util import http_status_to_code
from falcon.util import IS_64_BITS
from falcon.util import is_python_func
from falcon.util import mediatypes
from falcon.util import misc
from falcon.util import parse_header
from falcon.util import reader
from falcon.util import runs_sync
from falcon.util import secure_filename
from falcon.util import structures
from falcon.util import sync
from falcon.util import sync_to_async
from falcon.util import sys  # NOQA: F401
from falcon.util import time
from falcon.util import TimezoneGMT
from falcon.util import to_query_str
from falcon.util import uri
from falcon.util import wrap_sync_to_async
from falcon.util import wrap_sync_to_async_unsafe

# Package version
from falcon.version import __version__  # NOQA: F401

# NOTE(kgriffs): Only to be used internally on the rare occasion that we
#   need to log something that we can't communicate any other way.
_logger = _logging.getLogger('falcon')
_logger.addHandler(_logging.NullHandler())
