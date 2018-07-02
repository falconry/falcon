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

"""HTTP status constants."""

import itertools

from falcon.util.status_enum import BaseHTTPStatus

try:
    from http import HTTPStatus
except ImportError:
    from falcon.util.status_enum import HTTPStatus


class HTCPCPStatus(BaseHTTPStatus):
    IM_A_TEAPOT = 418, "I'm a teapot"


class HTTPStatusExtensions(BaseHTTPStatus):
    UNAVAILABLE_FOR_LEGAL_REASONS = 451, '451 Unavailable For Legal Reasons'


class HTTP7XXStatus(BaseHTTPStatus):
    """HTTP 7XX Developer Errors.

    See also: https://github.com/joho/7XX-rfc
    """

    # 70X - Inexcusable
    MEH = 701, 'Meh'
    EMACS = 702, 'Emacs'
    EXPLOSION = 703, 'Explosion'
    GOTO_FAIL = 704, 'Goto Fail'
    MISSED_THE_NECESSARY_VALIDATION_BY_AN_OVERSIGHT = 705, (
        'I wrote the code and missed the necessary validation by an oversight')
    DELETE_YOUR_ACCOUNT = 706, 'Delete Your Account'
    CANT_QUIT_VI = 707, "Can't quit vi"

    # 71X - Novelty Implementations
    PHP = 710, 'PHP'
    CONVENIENCE_STORE = 711, 'Convenience Store'
    NOSQL = 712, 'NoSQL'
    I_AM_NOT_A_TEAPOT = 718, 'I am not a teapot'
    HASKELL = 719, 'Haskell'

    # 72X - Edge Cases
    UNPOSSIBLE = 720, 'Unpossible'
    KNOWN_UNKNOWNS = 721, 'Known Unknowns'
    UNKNOWN_UNKNOWNS = 722, 'Unknown Unknowns'
    TRICKY = 723, 'Tricky'
    THIS_LINE_SHOULD_BE_UNREACHABLE = 724, 'This line should be unreachable'
    IT_WORKS_ON_MY_MACHINE = 725, 'It works on my machine'
    ITS_A_FEATURE_NOT_A_BUG = 726, "It's a feature, not a bug"
    THIRTY_TWO_BITS_IS_PLENTY = 727, '32 bits is plenty'
    IT_WORKS_IN_MY_TIMEZONE = 728, 'It works in my timezone'

    # 75X - Syntax Errors
    DIDNT_BOTHER_TO_COMPILE_IT = 750, "Didn't bother to compile it"
    SYNTAX_ERROR = 753, 'Syntax Error'
    TOO_MANY_SEMI_COLONS = 754, 'Too many semi-colons'
    NOT_ENOUGH_SEMI_COLONS = 755, 'Not enough semi-colons'
    INSUFFICIENTLY_POLITE = 756, 'Insufficiently polite'
    EXCESSIVELY_POLITE = 757, 'Excessively polite'
    UNEXPECTED_T_PAAMAYIM_NEKUDOTAYIM = 759, (
        'Unexpected "T_PAAMAYIM_NEKUDOTAYIM"')

    # 77X - Predictable Problems
    CACHED_FOR_TOO_LONG = 771, 'Cached for too long'
    NOT_CACHED_LONG_ENOUGH = 772, 'Not cached long enough'
    NOT_CACHED_AT_ALL = 773, 'Not cached at all'
    WHY_WAS_THIS_CACHED = 774, 'Why was this cached?'
    OUT_OF_CASH = 775, 'Out of cash'
    ERROR_ON_THE_EXCEPTION = 776, 'Error on the Exception'
    COINCIDENCE = 777, 'Coincidence'
    OFF_BY_ONE_ERROR = 778, 'Off By One Error'
    OFF_BY_TOO_MANY_TO_COUNT_ERROR = 779, 'Off By Too Many To Count Error'

    # 78X - Somebody Else's Problem
    PROJECT_OWNER_NOT_RESPONDING = 780, 'Project owner not responding'
    OPERATIONS = 781, 'Operations'
    QA = 782, 'QA'
    IT_WAS_A_CUSTOMER_REQUEST_HONESTLY = 783, (
        'It was a customer request, honestly')
    MANAGEMENT_OBVIOUSLY = 784, 'Management, obviously'
    TPS_COVER_SHEET_NOT_ATTACHED = 785, 'TPS Cover Sheet not attached'
    TRY_IT_NOW = 786, 'Try it now'
    FURTHER_FUNDING_REQUIRED = 787, 'Further Funding Required'
    DESIGNERS_FINAL_DESIGNS_WERENT = 788, "Designer's final designs weren't"
    NOT_MY_DEPARTMENT = 789, 'Not my department'

    # 79X - Internet crashed
    THE_INTERNET_SHUT_DOWN_DUE_TO_COPYRIGHT_RESTRICTIONS = 791, (
        'The Internet shut down due to copyright restrictions')
    CLIMATE_CHANGE_DRIVEN_CATASTROPHIC_WEATHER_EVENT = 792, (
        'Climate change driven catastrophic weather event')
    ZOMBIE_APOCALYPSE = 793, 'Zombie Apocalypse'
    SOMEONE_LET_PG_NEAR_A_REPL = 794, 'Someone let PG near a REPL'
    HEARTBLEED = 795, '#heartbleed'
    THIS_IS_THE_LAST_PAGE_OF_THE_INTERNET_GO_BACK = 797, (
        'This is the last page of the Internet.  Go back')
    I_CHECKED_THE_DB_BACKUPS_CUPBOARD_AND_THE_CUPBOARD_WAS_BARE = 798, (
        'I checked the db backups cupboard and the cupboard was bare')
    END_OF_THE_WORLD = 799, 'End of the world'


HTTP_100 = HTTPStatus(100)
HTTP_CONTINUE = HTTP_100
HTTP_101 = HTTPStatus(101)
HTTP_SWITCHING_PROTOCOLS = HTTP_101
HTTP_102 = HTTPStatus(102)
HTTP_PROCESSING = HTTP_102

HTTP_200 = HTTPStatus(200)
HTTP_OK = HTTP_200
HTTP_201 = HTTPStatus(201)
HTTP_CREATED = HTTP_201
HTTP_202 = HTTPStatus(202)
HTTP_ACCEPTED = HTTP_202
HTTP_203 = HTTPStatus(203)
HTTP_NON_AUTHORITATIVE_INFORMATION = HTTP_203
HTTP_204 = HTTPStatus(204)
HTTP_NO_CONTENT = HTTP_204
HTTP_205 = HTTPStatus(205)
HTTP_RESET_CONTENT = HTTP_205
HTTP_206 = HTTPStatus(206)
HTTP_PARTIAL_CONTENT = HTTP_206
HTTP_207 = HTTPStatus(207)
HTTP_MULTI_STATUS = HTTP_207
HTTP_208 = HTTPStatus(208)
HTTP_ALREADY_REPORTED = HTTP_208
HTTP_226 = HTTPStatus(226)
HTTP_IM_USED = HTTP_226

HTTP_300 = HTTPStatus(300)
HTTP_MULTIPLE_CHOICES = HTTP_300
HTTP_301 = HTTPStatus(301)
HTTP_MOVED_PERMANENTLY = HTTP_301
HTTP_302 = HTTPStatus(302)
HTTP_FOUND = HTTP_302
HTTP_303 = HTTPStatus(303)
HTTP_SEE_OTHER = HTTP_303
HTTP_304 = HTTPStatus(304)
HTTP_NOT_MODIFIED = HTTP_304
HTTP_305 = HTTPStatus(305)
HTTP_USE_PROXY = HTTP_305
HTTP_307 = HTTPStatus(307)
HTTP_TEMPORARY_REDIRECT = HTTP_307
HTTP_308 = HTTPStatus(308)
HTTP_PERMANENT_REDIRECT = HTTP_308

HTTP_400 = HTTPStatus(400)
HTTP_BAD_REQUEST = HTTP_400
HTTP_401 = HTTPStatus(401)
HTTP_UNAUTHORIZED = HTTP_401
HTTP_402 = HTTPStatus(402)
HTTP_PAYMENT_REQUIRED = HTTP_402
HTTP_403 = HTTPStatus(403)
HTTP_FORBIDDEN = HTTP_403
HTTP_404 = HTTPStatus(404)
HTTP_NOT_FOUND = HTTP_404
HTTP_405 = HTTPStatus(405)
HTTP_METHOD_NOT_ALLOWED = HTTP_405
HTTP_406 = HTTPStatus(406)
HTTP_NOT_ACCEPTABLE = HTTP_406
HTTP_407 = HTTPStatus(407)
HTTP_PROXY_AUTHENTICATION_REQUIRED = HTTP_407
HTTP_408 = HTTPStatus(408)
HTTP_REQUEST_TIMEOUT = HTTP_408
HTTP_409 = HTTPStatus(409)
HTTP_CONFLICT = HTTP_409
HTTP_410 = HTTPStatus(410)
HTTP_GONE = HTTP_410
HTTP_411 = HTTPStatus(411)
HTTP_LENGTH_REQUIRED = HTTP_411
HTTP_412 = HTTPStatus(412)
HTTP_PRECONDITION_FAILED = HTTP_412
HTTP_413 = HTTPStatus(413)
HTTP_REQUEST_ENTITY_TOO_LARGE = HTTP_413
HTTP_414 = HTTPStatus(414)
HTTP_REQUEST_URI_TOO_LONG = HTTP_414
HTTP_415 = HTTPStatus(415)
HTTP_UNSUPPORTED_MEDIA_TYPE = HTTP_415
HTTP_416 = HTTPStatus(416)
HTTP_REQUESTED_RANGE_NOT_SATISFIABLE = HTTP_416
HTTP_417 = HTTPStatus(417)
HTTP_EXPECTATION_FAILED = HTTP_417
HTTP_418 = HTCPCPStatus(418)
HTTP_IM_A_TEAPOT = HTTP_418
HTTP_422 = HTTPStatus(422)
HTTP_UNPROCESSABLE_ENTITY = HTTP_422
HTTP_423 = HTTPStatus(423)
HTTP_LOCKED = HTTP_423
HTTP_424 = HTTPStatus(424)
HTTP_FAILED_DEPENDENCY = HTTP_424
HTTP_426 = HTTPStatus(426)
HTTP_UPGRADE_REQUIRED = HTTP_426
HTTP_428 = HTTPStatus(428)
HTTP_PRECONDITION_REQUIRED = HTTP_428
HTTP_429 = HTTPStatus(429)
HTTP_TOO_MANY_REQUESTS = HTTP_429
HTTP_431 = HTTPStatus(431)
HTTP_REQUEST_HEADER_FIELDS_TOO_LARGE = HTTP_431
HTTP_451 = HTTPStatusExtensions(451)
HTTP_UNAVAILABLE_FOR_LEGAL_REASONS = HTTP_451

HTTP_500 = HTTPStatus(500)
HTTP_INTERNAL_SERVER_ERROR = HTTP_500
HTTP_501 = HTTPStatus(501)
HTTP_NOT_IMPLEMENTED = HTTP_501
HTTP_502 = HTTPStatus(502)
HTTP_BAD_GATEWAY = HTTP_502
HTTP_503 = HTTPStatus(503)
HTTP_SERVICE_UNAVAILABLE = HTTP_503
HTTP_504 = HTTPStatus(504)
HTTP_GATEWAY_TIMEOUT = HTTP_504
HTTP_505 = HTTPStatus(505)
HTTP_HTTP_VERSION_NOT_SUPPORTED = HTTP_505
HTTP_507 = HTTPStatus(507)
HTTP_INSUFFICIENT_STORAGE = HTTP_507
HTTP_508 = HTTPStatus(508)
HTTP_LOOP_DETECTED = HTTP_508
HTTP_511 = HTTPStatus(511)
HTTP_NETWORK_AUTHENTICATION_REQUIRED = HTTP_511

# 70X - Inexcusable
HTTP_701 = HTTP7XXStatus(701)
HTTP_702 = HTTP7XXStatus(702)
HTTP_703 = HTTP7XXStatus(703)
HTTP_704 = HTTP7XXStatus(704)
HTTP_705 = HTTP7XXStatus(705)
HTTP_706 = HTTP7XXStatus(706)
HTTP_707 = HTTP7XXStatus(707)

# 71X - Novelty Implementations
HTTP_710 = HTTP7XXStatus(710)
HTTP_711 = HTTP7XXStatus(711)
HTTP_712 = HTTP7XXStatus(712)
HTTP_718 = HTTP7XXStatus(718)
HTTP_719 = HTTP7XXStatus(719)

# 72X - Edge Cases
HTTP_720 = HTTP7XXStatus(720)
HTTP_721 = HTTP7XXStatus(721)
HTTP_722 = HTTP7XXStatus(722)
HTTP_723 = HTTP7XXStatus(723)
HTTP_724 = HTTP7XXStatus(724)
HTTP_725 = HTTP7XXStatus(725)
HTTP_726 = HTTP7XXStatus(726)
HTTP_727 = HTTP7XXStatus(727)
HTTP_728 = HTTP7XXStatus(728)

# 75X - Syntax Errors
HTTP_750 = HTTP7XXStatus(750)
HTTP_753 = HTTP7XXStatus(753)
HTTP_754 = HTTP7XXStatus(754)
HTTP_755 = HTTP7XXStatus(755)
HTTP_756 = HTTP7XXStatus(756)
HTTP_757 = HTTP7XXStatus(757)
HTTP_759 = HTTP7XXStatus(759)

# 77X - Predictable Problems
HTTP_771 = HTTP7XXStatus(771)
HTTP_772 = HTTP7XXStatus(772)
HTTP_773 = HTTP7XXStatus(773)
HTTP_774 = HTTP7XXStatus(774)
HTTP_775 = HTTP7XXStatus(775)
HTTP_776 = HTTP7XXStatus(776)
HTTP_777 = HTTP7XXStatus(777)
HTTP_778 = HTTP7XXStatus(778)
HTTP_779 = HTTP7XXStatus(779)

# 78X - Somebody Else's Problem
HTTP_780 = HTTP7XXStatus(780)
HTTP_781 = HTTP7XXStatus(781)
HTTP_782 = HTTP7XXStatus(782)
HTTP_783 = HTTP7XXStatus(783)
HTTP_784 = HTTP7XXStatus(784)
HTTP_785 = HTTP7XXStatus(785)
HTTP_786 = HTTP7XXStatus(786)
HTTP_787 = HTTP7XXStatus(787)
HTTP_788 = HTTP7XXStatus(788)
HTTP_789 = HTTP7XXStatus(789)

# 79X - Internet crashed
HTTP_791 = HTTP7XXStatus(791)
HTTP_792 = HTTP7XXStatus(792)
HTTP_793 = HTTP7XXStatus(793)
HTTP_794 = HTTP7XXStatus(794)
HTTP_795 = HTTP7XXStatus(795)
HTTP_797 = HTTP7XXStatus(797)
HTTP_798 = HTTP7XXStatus(798)
HTTP_799 = HTTP7XXStatus(799)


COMBINED_STATUS_CODES = {
    status: str(status.value) + ' ' + status.phrase
    for status in itertools.chain(HTTPStatus, HTTPStatusExtensions,
                                  HTCPCPStatus, HTTP7XXStatus)}
