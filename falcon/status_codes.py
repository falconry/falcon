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

HTTP_100 = '100 Continue'
HTTP_CONTINUE = HTTP_100
HTTP_101 = '101 Switching Protocols'
HTTP_SWITCHING_PROTOCOLS = HTTP_101
HTTP_102 = '102 Processing'
HTTP_PROCESSING = HTTP_102

HTTP_200 = '200 OK'
HTTP_OK = HTTP_200
HTTP_201 = '201 Created'
HTTP_CREATED = HTTP_201
HTTP_202 = '202 Accepted'
HTTP_ACCEPTED = HTTP_202
HTTP_203 = '203 Non-Authoritative Information'
HTTP_NON_AUTHORITATIVE_INFORMATION = HTTP_203
HTTP_204 = '204 No Content'
HTTP_NO_CONTENT = HTTP_204
HTTP_205 = '205 Reset Content'
HTTP_RESET_CONTENT = HTTP_205
HTTP_206 = '206 Partial Content'
HTTP_PARTIAL_CONTENT = HTTP_206
HTTP_207 = '207 Multi-Status'
HTTP_MULTI_STATUS = HTTP_207
HTTP_208 = '208 Already Reported'
HTTP_ALREADY_REPORTED = HTTP_208
HTTP_226 = '226 IM Used'
HTTP_IM_USED = HTTP_226

HTTP_300 = '300 Multiple Choices'
HTTP_MULTIPLE_CHOICES = HTTP_300
HTTP_301 = '301 Moved Permanently'
HTTP_MOVED_PERMANENTLY = HTTP_301
HTTP_302 = '302 Found'
HTTP_FOUND = HTTP_302
HTTP_303 = '303 See Other'
HTTP_SEE_OTHER = HTTP_303
HTTP_304 = '304 Not Modified'
HTTP_NOT_MODIFIED = HTTP_304
HTTP_305 = '305 Use Proxy'
HTTP_USE_PROXY = HTTP_305
HTTP_307 = '307 Temporary Redirect'
HTTP_TEMPORARY_REDIRECT = HTTP_307
HTTP_308 = '308 Permanent Redirect'
HTTP_PERMANENT_REDIRECT = HTTP_308

HTTP_400 = '400 Bad Request'
HTTP_BAD_REQUEST = HTTP_400
HTTP_401 = '401 Unauthorized'  # <-- Really means "unauthenticated"
HTTP_UNAUTHORIZED = HTTP_401
HTTP_402 = '402 Payment Required'
HTTP_PAYMENT_REQUIRED = HTTP_402
HTTP_403 = '403 Forbidden'  # <-- Really means "unauthorized"
HTTP_FORBIDDEN = HTTP_403
HTTP_404 = '404 Not Found'
HTTP_NOT_FOUND = HTTP_404
HTTP_405 = '405 Method Not Allowed'
HTTP_METHOD_NOT_ALLOWED = HTTP_405
HTTP_406 = '406 Not Acceptable'
HTTP_NOT_ACCEPTABLE = HTTP_406
HTTP_407 = '407 Proxy Authentication Required'
HTTP_PROXY_AUTHENTICATION_REQUIRED = HTTP_407
HTTP_408 = '408 Request Time-out'
HTTP_REQUEST_TIMEOUT = HTTP_408
HTTP_409 = '409 Conflict'
HTTP_CONFLICT = HTTP_409
HTTP_410 = '410 Gone'
HTTP_GONE = HTTP_410
HTTP_411 = '411 Length Required'
HTTP_LENGTH_REQUIRED = HTTP_411
HTTP_412 = '412 Precondition Failed'
HTTP_PRECONDITION_FAILED = HTTP_412
HTTP_413 = '413 Payload Too Large'
HTTP_REQUEST_ENTITY_TOO_LARGE = HTTP_413
HTTP_414 = '414 URI Too Long'
HTTP_REQUEST_URI_TOO_LONG = HTTP_414
HTTP_415 = '415 Unsupported Media Type'
HTTP_UNSUPPORTED_MEDIA_TYPE = HTTP_415
HTTP_416 = '416 Range Not Satisfiable'
HTTP_REQUESTED_RANGE_NOT_SATISFIABLE = HTTP_416
HTTP_417 = '417 Expectation Failed'
HTTP_EXPECTATION_FAILED = HTTP_417
HTTP_418 = "418 I'm a teapot"
HTTP_IM_A_TEAPOT = HTTP_418
HTTP_422 = '422 Unprocessable Entity'
HTTP_UNPROCESSABLE_ENTITY = HTTP_422
HTTP_423 = '423 Locked'
HTTP_LOCKED = HTTP_423
HTTP_424 = '424 Failed Dependency'
HTTP_FAILED_DEPENDENCY = HTTP_424
HTTP_426 = '426 Upgrade Required'
HTTP_UPGRADE_REQUIRED = HTTP_426
HTTP_428 = '428 Precondition Required'
HTTP_PRECONDITION_REQUIRED = HTTP_428
HTTP_429 = '429 Too Many Requests'
HTTP_TOO_MANY_REQUESTS = HTTP_429
HTTP_431 = '431 Request Header Fields Too Large'
HTTP_REQUEST_HEADER_FIELDS_TOO_LARGE = HTTP_431
HTTP_451 = '451 Unavailable For Legal Reasons'
HTTP_UNAVAILABLE_FOR_LEGAL_REASONS = HTTP_451

HTTP_500 = '500 Internal Server Error'
HTTP_INTERNAL_SERVER_ERROR = HTTP_500
HTTP_501 = '501 Not Implemented'
HTTP_NOT_IMPLEMENTED = HTTP_501
HTTP_502 = '502 Bad Gateway'
HTTP_BAD_GATEWAY = HTTP_502
HTTP_503 = '503 Service Unavailable'
HTTP_SERVICE_UNAVAILABLE = HTTP_503
HTTP_504 = '504 Gateway Timeout'
HTTP_GATEWAY_TIMEOUT = HTTP_504
HTTP_505 = '505 HTTP Version Not Supported'
HTTP_HTTP_VERSION_NOT_SUPPORTED = HTTP_505
HTTP_507 = '507 Insufficient Storage'
HTTP_INSUFFICIENT_STORAGE = HTTP_507
HTTP_508 = '508 Loop Detected'
HTTP_LOOP_DETECTED = HTTP_508
HTTP_511 = '511 Network Authentication Required'
HTTP_NETWORK_AUTHENTICATION_REQUIRED = HTTP_511

# 70X - Inexcusable
HTTP_701 = '701 Meh'
HTTP_702 = '702 Emacs'
HTTP_703 = '703 Explosion'

# 71X - Novelty Implementations
HTTP_710 = '710 PHP'
HTTP_711 = '711 Convenience Store'
HTTP_712 = '712 NoSQL'
HTTP_719 = '719 I am not a teapot'

# 72X - Edge Cases
HTTP_720 = '720 Unpossible'
HTTP_721 = '721 Known Unknowns'
HTTP_722 = '722 Unknown Unknowns'
HTTP_723 = '723 Tricky'
HTTP_724 = '724 This line should be unreachable'
HTTP_725 = '725 It works on my machine'
HTTP_726 = "726 It's a feature, not a bug"
HTTP_727 = '727 32 bits is plenty'

# 74X - Meme Driven
HTTP_740 = '740 Computer says no'
HTTP_741 = '741 Compiling'
HTTP_742 = '742 A kitten dies'
HTTP_743 = '743 I thought I knew regular expressions'
HTTP_744 = '744 Y U NO write integration tests?'
HTTP_745 = ("745 I don't always test my code, but when I do"
            'I do it in production')
HTTP_748 = '748 Confounded by Ponies'
HTTP_749 = '749 Reserved for Chuck Norris'

# 75X - Syntax Errors
HTTP_750 = "750 Didn't bother to compile it"
HTTP_753 = '753 Syntax Error'
HTTP_754 = '754 Too many semi-colons'
HTTP_755 = '755 Not enough semi-colons'
HTTP_759 = '759 Unexpected T_PAAMAYIM_NEKUDOTAYIM'

# 77X - Predictable Problems
HTTP_771 = '771 Cached for too long'
HTTP_772 = '772 Not cached long enough'
HTTP_773 = '773 Not cached at all'
HTTP_774 = '774 Why was this cached?'
HTTP_776 = '776 Error on the Exception'
HTTP_777 = '777 Coincidence'
HTTP_778 = '778 Off By One Error'
HTTP_779 = '779 Off By Too Many To Count Error'

# 78X - Somebody Else's Problem
HTTP_780 = '780 Project owner not responding'
HTTP_781 = '781 Operations'
HTTP_782 = '782 QA'
HTTP_783 = '783 It was a customer request, honestly'
HTTP_784 = '784 Management, obviously'
HTTP_785 = '785 TPS Cover Sheet not attached'
HTTP_786 = '786 Try it now'

# 79X - Internet crashed
HTTP_791 = '791 The Internet shut down due to copyright restrictions'
HTTP_792 = '792 Climate change driven catastrophic weather event'
HTTP_797 = '797 This is the last page of the Internet. Go back'
HTTP_799 = '799 End of the world'
