"""Defines HTTP status codes.

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

"""

HTTP_100 = '100 Continue'
HTTP_101 = '101 Switching Protocols'

HTTP_200 = '200 OK'
HTTP_201 = '201 Created'
HTTP_202 = '202 Accepted'
HTTP_203 = '203 Non-Authoritative Information'
HTTP_204 = '204 No Content'
HTTP_205 = '205 Reset Content'
HTTP_206 = '206 Partial Content'
HTTP_226 = '226 IM Used'

# TODO: 3xx
HTTP_300 = '300 Multiple Choices'
HTTP_301 = '301 Moved Permanently'
HTTP_302 = '302 Found'
HTTP_303 = '303 See Other'
HTTP_304 = '304 Not Modified'
HTTP_305 = '305 Use Proxy'
HTTP_307 = '307 Temporary Redirect'

HTTP_400 = '400 Bad Request'
HTTP_401 = '401 Unauthorized'  # <-- Really means "unauthenticated"
HTTP_402 = '402 Payment Required'
HTTP_403 = '403 Forbidden'  # <-- Really means "unauthorized"
HTTP_404 = '404 Not Found'
HTTP_405 = '405 Method Not Allowed'
HTTP_406 = '406 Not Acceptable'
HTTP_407 = '407 Proxy Authentication Required'
HTTP_408 = '408 Request Time-out'
HTTP_409 = '409 Conflict'
HTTP_410 = '410 Gone'
HTTP_411 = '411 Length Required'
HTTP_412 = '412 Precondition Failed'
HTTP_413 = '413 Payload Too Large'
HTTP_414 = '414 URI Too Long'
HTTP_415 = '415 Unsupported Media Type'
HTTP_416 = '416 Range Not Satisfiable'
HTTP_417 = '417 Expectation Failed'
HTTP_418 = "418 I'm a teapot"
HTTP_426 = '426 Upgrade Required'

HTTP_500 = '500 Internal Server Error'
HTTP_501 = '501 Not Implemented'
HTTP_502 = '502 Bad Gateway'
HTTP_503 = '503 Service Unavailable'
HTTP_504 = '504 Gateway Time-out'
HTTP_505 = '505 HTTP Version not supported'

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
            "I do it in production")
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
