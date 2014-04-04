.. _status:

Status Codes
============

Falcon provides a list of constants for common
`HTTP response status codes <http://httpstatus.es>`_
that you can use like so:

.. code:: python

    # Override the default "200 OK" response status
    resp.status = falcon.HTTP_409

1xx Informational
-----------------

.. code:: python

    HTTP_100 = '100 Continue'
    HTTP_101 = '101 Switching Protocols'

2xx Success
-----------

.. code:: python

    HTTP_200 = '200 OK'
    HTTP_201 = '201 Created'
    HTTP_202 = '202 Accepted'
    HTTP_203 = '203 Non-Authoritative Information'
    HTTP_204 = '204 No Content'
    HTTP_205 = '205 Reset Content'
    HTTP_206 = '206 Partial Content'
    HTTP_226 = '226 IM Used'

3xx Redirection
---------------

.. code:: python

    HTTP_300 = '300 Multiple Choices'
    HTTP_301 = '301 Moved Permanently'
    HTTP_302 = '302 Found'
    HTTP_303 = '303 See Other'
    HTTP_304 = '304 Not Modified'
    HTTP_305 = '305 Use Proxy'
    HTTP_307 = '307 Temporary Redirect'

4xx Client Error
----------------

.. code:: python

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

5xx Server Error
----------------

.. code:: python

    HTTP_500 = '500 Internal Server Error'
    HTTP_501 = '501 Not Implemented'
    HTTP_502 = '502 Bad Gateway'
    HTTP_503 = '503 Service Unavailable'
    HTTP_504 = '504 Gateway Time-out'
    HTTP_505 = '505 HTTP Version not supported'
