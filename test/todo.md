
Functionality

* Test sending/receiving various status codes
* Chunked transfer encoding, streaming 0, some, and lots of bytes
  * Add tips to NOTES.md
  * Framework should automatically set content-length for smaller streams, and only enable chunked encoding for really big ones AND when *not* using HTTP/1.0.
* Ensure req dict has things the app needs, including path, user agent, various headers.
* Test default http status code (200 OK?)
* Test compiling routes, throwing on invalid routes (such as missing initial forward slash or non-ascii)
* Figure out encoding of body and stream - test that the framework requires byte strings or a byte string generator (for body and stream attributes of resp, respectively)
* Test custom error handlers - customizing error document at least
* Test async middleware ala rproxy
* Test setting different routes for different verbs
* Test throwing an exception from within a handler
* Test neglecting to set a body
* Test neglecting to set a status
* Test passing bad arguments to add_route
* Test other kinds of routes - empty, root, multiple levels
* Test URI-template parsing (precompile)
* Test passing a shared dict to each mock call (e.g., db connections, config)...and that it is passed to the request handler correctly
* Test pre/post filters
* Test error handling with standard response (for all error classes?)
* Test passing bogus data to create_api and/or add_route

Performance

* Test inlining functions, maybe make a tool that does this automatically
* Try using a closure to generate the WSGI request handler (vs. a class)
  
