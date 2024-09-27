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

"""HTTP status line constants."""

from typing import Final

# 1xx - Informational
HTTP_100: Final[str] = '100 Continue'
HTTP_CONTINUE: Final[str] = HTTP_100
HTTP_101: Final[str] = '101 Switching Protocols'
HTTP_SWITCHING_PROTOCOLS: Final[str] = HTTP_101
HTTP_102: Final[str] = '102 Processing'
HTTP_PROCESSING: Final[str] = HTTP_102
HTTP_103: Final[str] = '103 Early Hints'
HTTP_EARLY_HINTS: Final[str] = HTTP_103

# 2xx - Success
HTTP_200: Final[str] = '200 OK'
HTTP_OK: Final[str] = HTTP_200
HTTP_201: Final[str] = '201 Created'
HTTP_CREATED: Final[str] = HTTP_201
HTTP_202: Final[str] = '202 Accepted'
HTTP_ACCEPTED: Final[str] = HTTP_202
HTTP_203: Final[str] = '203 Non-Authoritative Information'
HTTP_NON_AUTHORITATIVE_INFORMATION: Final[str] = HTTP_203
HTTP_204: Final[str] = '204 No Content'
HTTP_NO_CONTENT: Final[str] = HTTP_204
HTTP_205: Final[str] = '205 Reset Content'
HTTP_RESET_CONTENT: Final[str] = HTTP_205
HTTP_206: Final[str] = '206 Partial Content'
HTTP_PARTIAL_CONTENT: Final[str] = HTTP_206
HTTP_207: Final[str] = '207 Multi-Status'
HTTP_MULTI_STATUS: Final[str] = HTTP_207
HTTP_208: Final[str] = '208 Already Reported'
HTTP_ALREADY_REPORTED: Final[str] = HTTP_208
HTTP_226: Final[str] = '226 IM Used'
HTTP_IM_USED: Final[str] = HTTP_226

# 3xx - Redirection
HTTP_300: Final[str] = '300 Multiple Choices'
HTTP_MULTIPLE_CHOICES: Final[str] = HTTP_300
HTTP_301: Final[str] = '301 Moved Permanently'
HTTP_MOVED_PERMANENTLY: Final[str] = HTTP_301
HTTP_302: Final[str] = '302 Found'
HTTP_FOUND: Final[str] = HTTP_302
HTTP_303: Final[str] = '303 See Other'
HTTP_SEE_OTHER: Final[str] = HTTP_303
HTTP_304: Final[str] = '304 Not Modified'
HTTP_NOT_MODIFIED: Final[str] = HTTP_304
HTTP_305: Final[str] = '305 Use Proxy'
HTTP_USE_PROXY: Final[str] = HTTP_305
HTTP_307: Final[str] = '307 Temporary Redirect'
HTTP_TEMPORARY_REDIRECT: Final[str] = HTTP_307
HTTP_308: Final[str] = '308 Permanent Redirect'
HTTP_PERMANENT_REDIRECT: Final[str] = HTTP_308

# 4xx - Client Error
HTTP_400: Final[str] = '400 Bad Request'
HTTP_BAD_REQUEST: Final[str] = HTTP_400
HTTP_401: Final[str] = '401 Unauthorized'  # <-- Really means "unauthenticated"
HTTP_UNAUTHORIZED: Final[str] = HTTP_401
HTTP_402: Final[str] = '402 Payment Required'
HTTP_PAYMENT_REQUIRED: Final[str] = HTTP_402
HTTP_403: Final[str] = '403 Forbidden'  # <-- Really means "unauthorized"
HTTP_FORBIDDEN: Final[str] = HTTP_403
HTTP_404: Final[str] = '404 Not Found'
HTTP_NOT_FOUND: Final[str] = HTTP_404
HTTP_405: Final[str] = '405 Method Not Allowed'
HTTP_METHOD_NOT_ALLOWED: Final[str] = HTTP_405
HTTP_406: Final[str] = '406 Not Acceptable'
HTTP_NOT_ACCEPTABLE: Final[str] = HTTP_406
HTTP_407: Final[str] = '407 Proxy Authentication Required'
HTTP_PROXY_AUTHENTICATION_REQUIRED: Final[str] = HTTP_407
HTTP_408: Final[str] = '408 Request Timeout'
HTTP_REQUEST_TIMEOUT: Final[str] = HTTP_408
HTTP_409: Final[str] = '409 Conflict'
HTTP_CONFLICT: Final[str] = HTTP_409
HTTP_410: Final[str] = '410 Gone'
HTTP_GONE: Final[str] = HTTP_410
HTTP_411: Final[str] = '411 Length Required'
HTTP_LENGTH_REQUIRED: Final[str] = HTTP_411
HTTP_412: Final[str] = '412 Precondition Failed'
HTTP_PRECONDITION_FAILED: Final[str] = HTTP_412
HTTP_413: Final[str] = '413 Content Too Large'
HTTP_CONTENT_TOO_LARGE: Final[str] = HTTP_413
HTTP_PAYLOAD_TOO_LARGE: Final[str] = HTTP_413
HTTP_REQUEST_ENTITY_TOO_LARGE: Final[str] = HTTP_413
HTTP_414: Final[str] = '414 URI Too Long'
HTTP_REQUEST_URI_TOO_LONG: Final[str] = HTTP_414
HTTP_415: Final[str] = '415 Unsupported Media Type'
HTTP_UNSUPPORTED_MEDIA_TYPE: Final[str] = HTTP_415
HTTP_416: Final[str] = '416 Range Not Satisfiable'
HTTP_REQUESTED_RANGE_NOT_SATISFIABLE: Final[str] = HTTP_416
HTTP_417: Final[str] = '417 Expectation Failed'
HTTP_EXPECTATION_FAILED: Final[str] = HTTP_417
HTTP_418: Final[str] = "418 I'm a teapot"
HTTP_IM_A_TEAPOT: Final[str] = HTTP_418
HTTP_421: Final[str] = '421 Misdirected Request'
HTTP_MISDIRECTED_REQUEST: Final[str] = HTTP_421
HTTP_422: Final[str] = '422 Unprocessable Entity'
HTTP_UNPROCESSABLE_ENTITY: Final[str] = HTTP_422
HTTP_423: Final[str] = '423 Locked'
HTTP_LOCKED: Final[str] = HTTP_423
HTTP_424: Final[str] = '424 Failed Dependency'
HTTP_FAILED_DEPENDENCY: Final[str] = HTTP_424
HTTP_425: Final[str] = '425 Too Early'
HTTP_TOO_EARLY: Final[str] = HTTP_425
HTTP_426: Final[str] = '426 Upgrade Required'
HTTP_UPGRADE_REQUIRED: Final[str] = HTTP_426
HTTP_428: Final[str] = '428 Precondition Required'
HTTP_PRECONDITION_REQUIRED: Final[str] = HTTP_428
HTTP_429: Final[str] = '429 Too Many Requests'
HTTP_TOO_MANY_REQUESTS: Final[str] = HTTP_429
HTTP_431: Final[str] = '431 Request Header Fields Too Large'
HTTP_REQUEST_HEADER_FIELDS_TOO_LARGE: Final[str] = HTTP_431
HTTP_451: Final[str] = '451 Unavailable For Legal Reasons'
HTTP_UNAVAILABLE_FOR_LEGAL_REASONS: Final[str] = HTTP_451

# 5xx - Server Error
HTTP_500: Final[str] = '500 Internal Server Error'
HTTP_INTERNAL_SERVER_ERROR: Final[str] = HTTP_500
HTTP_501: Final[str] = '501 Not Implemented'
HTTP_NOT_IMPLEMENTED: Final[str] = HTTP_501
HTTP_502: Final[str] = '502 Bad Gateway'
HTTP_BAD_GATEWAY: Final[str] = HTTP_502
HTTP_503: Final[str] = '503 Service Unavailable'
HTTP_SERVICE_UNAVAILABLE: Final[str] = HTTP_503
HTTP_504: Final[str] = '504 Gateway Timeout'
HTTP_GATEWAY_TIMEOUT: Final[str] = HTTP_504
HTTP_505: Final[str] = '505 HTTP Version Not Supported'
HTTP_HTTP_VERSION_NOT_SUPPORTED: Final[str] = HTTP_505
HTTP_506: Final[str] = '506 Variant Also Negotiates'
HTTP_VARIANT_ALSO_NEGOTIATES: Final[str] = HTTP_506
HTTP_507: Final[str] = '507 Insufficient Storage'
HTTP_INSUFFICIENT_STORAGE: Final[str] = HTTP_507
HTTP_508: Final[str] = '508 Loop Detected'
HTTP_LOOP_DETECTED: Final[str] = HTTP_508
HTTP_510: Final[str] = '510 Not Extended'
HTTP_NOT_EXTENDED: Final[str] = HTTP_510
HTTP_511: Final[str] = '511 Network Authentication Required'
HTTP_NETWORK_AUTHENTICATION_REQUIRED: Final[str] = HTTP_511

# 70X - Inexcusable
HTTP_701: Final[str] = '701 Meh'
HTTP_702: Final[str] = '702 Emacs'
HTTP_703: Final[str] = '703 Explosion'

# 71X - Novelty Implementations
HTTP_710: Final[str] = '710 PHP'
HTTP_711: Final[str] = '711 Convenience Store'
HTTP_712: Final[str] = '712 NoSQL'
HTTP_719: Final[str] = '719 I am not a teapot'

# 72X - Edge Cases
HTTP_720: Final[str] = '720 Unpossible'
HTTP_721: Final[str] = '721 Known Unknowns'
HTTP_722: Final[str] = '722 Unknown Unknowns'
HTTP_723: Final[str] = '723 Tricky'
HTTP_724: Final[str] = '724 This line should be unreachable'
HTTP_725: Final[str] = '725 It works on my machine'
HTTP_726: Final[str] = "726 It's a feature, not a bug"
HTTP_727: Final[str] = '727 32 bits is plenty'

# 74X - Meme Driven
HTTP_740: Final[str] = '740 Computer says no'
HTTP_741: Final[str] = '741 Compiling'
HTTP_742: Final[str] = '742 A kitten dies'
HTTP_743: Final[str] = '743 I thought I knew regular expressions'
HTTP_744: Final[str] = '744 Y U NO write integration tests?'
HTTP_745: Final[str] = (
    "745 I don't always test my code, but when I do I do it in production"
)
HTTP_748: Final[str] = '748 Confounded by Ponies'
HTTP_749: Final[str] = '749 Reserved for Chuck Norris'

# 75X - Syntax Errors
HTTP_750: Final[str] = "750 Didn't bother to compile it"
HTTP_753: Final[str] = '753 Syntax Error'
HTTP_754: Final[str] = '754 Too many semi-colons'
HTTP_755: Final[str] = '755 Not enough semi-colons'
HTTP_759: Final[str] = '759 Unexpected T_PAAMAYIM_NEKUDOTAYIM'

# 77X - Predictable Problems
HTTP_771: Final[str] = '771 Cached for too long'
HTTP_772: Final[str] = '772 Not cached long enough'
HTTP_773: Final[str] = '773 Not cached at all'
HTTP_774: Final[str] = '774 Why was this cached?'
HTTP_776: Final[str] = '776 Error on the Exception'
HTTP_777: Final[str] = '777 Coincidence'
HTTP_778: Final[str] = '778 Off By One Error'
HTTP_779: Final[str] = '779 Off By Too Many To Count Error'

# 78X - Somebody Else's Problem
HTTP_780: Final[str] = '780 Project owner not responding'
HTTP_781: Final[str] = '781 Operations'
HTTP_782: Final[str] = '782 QA'
HTTP_783: Final[str] = '783 It was a customer request, honestly'
HTTP_784: Final[str] = '784 Management, obviously'
HTTP_785: Final[str] = '785 TPS Cover Sheet not attached'
HTTP_786: Final[str] = '786 Try it now'

# 79X - Internet crashed
HTTP_791: Final[str] = '791 The Internet shut down due to copyright restrictions'
HTTP_792: Final[str] = '792 Climate change driven catastrophic weather event'
HTTP_797: Final[str] = '797 This is the last page of the Internet. Go back'
HTTP_799: Final[str] = '799 End of the world'

__all__ = (
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
