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

# 1xx - Informational
HTTP_100 = HTTP_CONTINUE = '100 Continue'
HTTP_101 = HTTP_SWITCHING_PROTOCOLS = '101 Switching Protocols'
HTTP_102 = HTTP_PROCESSING = '102 Processing'

# 2xx - Success
HTTP_200 = HTTP_OK = '200 OK'
HTTP_201 = HTTP_CREATED = '201 Created'
HTTP_202 = HTTP_ACCEPTED = '202 Accepted'
HTTP_203 = HTTP_NON_AUTHORITATIVE_INFORMATION = '203 Non-Authoritative Information'
HTTP_204 = HTTP_NO_CONTENT = '204 No Content'
HTTP_205 = HTTP_RESET_CONTENT = '205 Reset Content'
HTTP_206 = HTTP_PARTIAL_CONTENT = '206 Partial Content'
HTTP_207 = HTTP_MULTI_STATUS = '207 Multi-Status'
HTTP_208 = HTTP_ALREADY_REPORTED = '208 Already Reported'
HTTP_226 = HTTP_IM_USED = '226 IM Used'

# 3xx - Redirection
HTTP_300 = HTTP_MULTIPLE_CHOICES = '300 Multiple Choices'
HTTP_301 = HTTP_MOVED_PERMANENTLY = '301 Moved Permanently'
HTTP_302 = HTTP_FOUND = '302 Found'
HTTP_303 = HTTP_SEE_OTHER = '303 See Other'
HTTP_304 = HTTP_NOT_MODIFIED = '304 Not Modified'
HTTP_305 = HTTP_USE_PROXY = '305 Use Proxy'
HTTP_307 = HTTP_TEMPORARY_REDIRECT = '307 Temporary Redirect'
HTTP_308 = HTTP_PERMANENT_REDIRECT = '308 Permanent Redirect'

# 4xx - Client Error
HTTP_400 = HTTP_BAD_REQUEST = '400 Bad Request'
HTTP_401 = HTTP_UNAUTHORIZED = '401 Unauthorized'  # <-- Really means "unauthenticated"
HTTP_402 = HTTP_PAYMENT_REQUIRED = '402 Payment Required'
HTTP_403 = HTTP_FORBIDDEN = '403 Forbidden'  # <-- Really means "unauthorized"
HTTP_404 = HTTP_NOT_FOUND = '404 Not Found'
HTTP_405 = HTTP_METHOD_NOT_ALLOWED = '405 Method Not Allowed'
HTTP_406 = HTTP_NOT_ACCEPTABLE = '406 Not Acceptable'
HTTP_407 = HTTP_PROXY_AUTHENTICATION_REQUIRED = '407 Proxy Authentication Required'
HTTP_408 = HTTP_REQUEST_TIMEOUT = '408 Request Timeout'
HTTP_409 = HTTP_CONFLICT = '409 Conflict'
HTTP_410 = HTTP_GONE = '410 Gone'
HTTP_411 = HTTP_LENGTH_REQUIRED = '411 Length Required'
HTTP_412 = HTTP_PRECONDITION_FAILED = '412 Precondition Failed'
HTTP_413 = HTTP_REQUEST_ENTITY_TOO_LARGE = '413 Payload Too Large'
HTTP_414 = HTTP_REQUEST_URI_TOO_LONG = '414 URI Too Long'
HTTP_415 = HTTP_UNSUPPORTED_MEDIA_TYPE = '415 Unsupported Media Type'
HTTP_416 = HTTP_REQUESTED_RANGE_NOT_SATISFIABLE = '416 Range Not Satisfiable'
HTTP_417 = HTTP_EXPECTATION_FAILED = '417 Expectation Failed'
HTTP_418 = HTTP_IM_A_TEAPOT = "418 I'm a teapot"
HTTP_422 = HTTP_UNPROCESSABLE_ENTITY = '422 Unprocessable Entity'
HTTP_423 = HTTP_LOCKED = '423 Locked'
HTTP_424 = HTTP_FAILED_DEPENDENCY = '424 Failed Dependency'
HTTP_426 = HTTP_UPGRADE_REQUIRED = '426 Upgrade Required'
HTTP_428 = HTTP_PRECONDITION_REQUIRED = '428 Precondition Required'
HTTP_429 = HTTP_TOO_MANY_REQUESTS = '429 Too Many Requests'
HTTP_431 = HTTP_REQUEST_HEADER_FIELDS_TOO_LARGE = '431 Request Header Fields Too Large'
HTTP_451 = HTTP_UNAVAILABLE_FOR_LEGAL_REASONS = '451 Unavailable For Legal Reasons'

# 5xx - Server Error
HTTP_500 = HTTP_INTERNAL_SERVER_ERROR = '500 Internal Server Error'
HTTP_501 = HTTP_NOT_IMPLEMENTED = '501 Not Implemented'
HTTP_502 = HTTP_BAD_GATEWAY = '502 Bad Gateway'
HTTP_503 = HTTP_SERVICE_UNAVAILABLE = '503 Service Unavailable'
HTTP_504 = HTTP_GATEWAY_TIMEOUT = '504 Gateway Timeout'
HTTP_505 = HTTP_HTTP_VERSION_NOT_SUPPORTED = '505 HTTP Version Not Supported'
HTTP_507 = HTTP_INSUFFICIENT_STORAGE = '507 Insufficient Storage'
HTTP_508 = HTTP_LOOP_DETECTED = '508 Loop Detected'
HTTP_511 = HTTP_NETWORK_AUTHENTICATION_REQUIRED = '511 Network Authentication Required'

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
HTTP_745 = "745 I don't always test my code, but when I do" 'I do it in production'
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
