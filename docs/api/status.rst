.. _status:

Status Codes
============

Falcon provides a list of constants for common
`HTTP response status codes <http://httpstatus.es>`_.

For example:

.. code:: python

    # Override the default "200 OK" response status
    resp.status = falcon.HTTP_409

Or, using the more verbose name:

.. code:: python

    resp.status = falcon.HTTP_CONFLICT

Using these constants helps avoid typos and cuts down on the number of
string objects that must be created when preparing responses.

Falcon also provides a generic `HTTPStatus` class. Raise this class from a hook,
middleware, or a responder to stop handling the request and skip to the response
handling. It takes status, additional headers and body as input arguments.

HTTPStatus
----------

.. autoclass:: falcon.HTTPStatus
    :members:


1xx Informational
-----------------

.. code:: python

    HTTP_CONTINUE = HTTP_100
    HTTP_SWITCHING_PROTOCOLS = HTTP_101
    HTTP_PROCESSING = HTTP_102

    HTTP_100 = '100 Continue'
    HTTP_101 = '101 Switching Protocols'
    HTTP_102 = '102 Processing'

2xx Success
-----------

.. code:: python

    HTTP_OK = HTTP_200
    HTTP_CREATED = HTTP_201
    HTTP_ACCEPTED = HTTP_202
    HTTP_NON_AUTHORITATIVE_INFORMATION = HTTP_203
    HTTP_NO_CONTENT = HTTP_204
    HTTP_RESET_CONTENT = HTTP_205
    HTTP_PARTIAL_CONTENT = HTTP_206
    HTTP_MULTI_STATUS = HTTP_207
    HTTP_ALREADY_REPORTED = HTTP_208
    HTTP_IM_USED = HTTP_226

    HTTP_200 = '200 OK'
    HTTP_201 = '201 Created'
    HTTP_202 = '202 Accepted'
    HTTP_203 = '203 Non-Authoritative Information'
    HTTP_204 = '204 No Content'
    HTTP_205 = '205 Reset Content'
    HTTP_206 = '206 Partial Content'
    HTTP_207 = '207 Multi-Status'
    HTTP_208 = '208 Already Reported'
    HTTP_226 = '226 IM Used'

3xx Redirection
---------------

.. code:: python

    HTTP_MULTIPLE_CHOICES = HTTP_300
    HTTP_MOVED_PERMANENTLY = HTTP_301
    HTTP_FOUND = HTTP_302
    HTTP_SEE_OTHER = HTTP_303
    HTTP_NOT_MODIFIED = HTTP_304
    HTTP_USE_PROXY = HTTP_305
    HTTP_TEMPORARY_REDIRECT = HTTP_307
    HTTP_PERMANENT_REDIRECT = HTTP_308

    HTTP_300 = '300 Multiple Choices'
    HTTP_301 = '301 Moved Permanently'
    HTTP_302 = '302 Found'
    HTTP_303 = '303 See Other'
    HTTP_304 = '304 Not Modified'
    HTTP_305 = '305 Use Proxy'
    HTTP_307 = '307 Temporary Redirect'
    HTTP_308 = '308 Permanent Redirect'

4xx Client Error
----------------

.. code:: python

    HTTP_BAD_REQUEST = HTTP_400
    HTTP_UNAUTHORIZED = HTTP_401  # <-- Really means "unauthenticated"
    HTTP_PAYMENT_REQUIRED = HTTP_402
    HTTP_FORBIDDEN = HTTP_403  # <-- Really means "unauthorized"
    HTTP_NOT_FOUND = HTTP_404
    HTTP_METHOD_NOT_ALLOWED = HTTP_405
    HTTP_NOT_ACCEPTABLE = HTTP_406
    HTTP_PROXY_AUTHENTICATION_REQUIRED = HTTP_407
    HTTP_REQUEST_TIMEOUT = HTTP_408
    HTTP_CONFLICT = HTTP_409
    HTTP_GONE = HTTP_410
    HTTP_LENGTH_REQUIRED = HTTP_411
    HTTP_PRECONDITION_FAILED = HTTP_412
    HTTP_REQUEST_ENTITY_TOO_LARGE = HTTP_413
    HTTP_REQUEST_URI_TOO_LONG = HTTP_414
    HTTP_UNSUPPORTED_MEDIA_TYPE = HTTP_415
    HTTP_REQUESTED_RANGE_NOT_SATISFIABLE = HTTP_416
    HTTP_EXPECTATION_FAILED = HTTP_417
    HTTP_IM_A_TEAPOT = HTTP_418
    HTTP_UNPROCESSABLE_ENTITY = HTTP_422
    HTTP_LOCKED = HTTP_423
    HTTP_FAILED_DEPENDENCY = HTTP_424
    HTTP_UPGRADE_REQUIRED = HTTP_426
    HTTP_PRECONDITION_REQUIRED = HTTP_428
    HTTP_TOO_MANY_REQUESTS = HTTP_429
    HTTP_REQUEST_HEADER_FIELDS_TOO_LARGE = HTTP_431
    HTTP_UNAVAILABLE_FOR_LEGAL_REASONS = HTTP_451

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
    HTTP_422 = "422 Unprocessable Entity"
    HTTP_423 = '423 Locked'
    HTTP_424 = '424 Failed Dependency'
    HTTP_426 = '426 Upgrade Required'
    HTTP_428 = '428 Precondition Required'
    HTTP_429 = '429 Too Many Requests'
    HTTP_431 = '431 Request Header Fields Too Large'
    HTTP_451 = '451 Unavailable For Legal Reasons'

5xx Server Error
----------------

.. code:: python

    HTTP_INTERNAL_SERVER_ERROR = HTTP_500
    HTTP_NOT_IMPLEMENTED = HTTP_501
    HTTP_BAD_GATEWAY = HTTP_502
    HTTP_SERVICE_UNAVAILABLE = HTTP_503
    HTTP_GATEWAY_TIMEOUT = HTTP_504
    HTTP_HTTP_VERSION_NOT_SUPPORTED = HTTP_505
    HTTP_INSUFFICIENT_STORAGE = HTTP_507
    HTTP_LOOP_DETECTED = HTTP_508
    HTTP_NETWORK_AUTHENTICATION_REQUIRED = HTTP_511

    HTTP_500 = '500 Internal Server Error'
    HTTP_501 = '501 Not Implemented'
    HTTP_502 = '502 Bad Gateway'
    HTTP_503 = '503 Service Unavailable'
    HTTP_504 = '504 Gateway Time-out'
    HTTP_505 = '505 HTTP Version not supported'
    HTTP_507 = '507 Insufficient Storage'
    HTTP_508 = '508 Loop Detected'
    HTTP_511 = '511 Network Authentication Required'
