0.2.0
=====

New
---

-  Since 0.1 we've added proper RTD docs to make it easier for everyone
   to get started with the framework. Over time we will continue adding
   content, and we would love your help!
-  Falcon now supports "wsgi.filewrapper". You can assign any file-like
   object to resp.stream and Falcon will use "wsgi.filewrapper" to more
   efficiently pipe the data to the WSGI server.
-  Support was added for automatically parsing requests containing
   "application/x-www-form-urlencoded" content. Form fields are now
   folded into req.params.
-  Custom Request and Response classes are now supported. You can
   specify custom types when instantiating falcon.API.
-  A new middleware feature was added to the framework. Middleware
   deprecates global hooks, and we encourage everyone to migrate as soon
   as possible.
-  A general-purpose dict attribute was added to Request. Middleware,
   hooks, and responders can now use req.context to share contextual
   information about the current request.
-  A new method, append\_header, was added to falcon.API to allow
   setting multiple values for the same header using comma separation.
   Note that this will not work for setting cookies, but we plan to
   address this in the next release (0.3).
-  A new "resource" attribute was added to hooks. Old hooks that do not
   accept this new attribute are shimmed so that they will continue to
   function. While we have worked hard to minimize the performance
   impact, we recommend migrating to the new function signature to avoid
   any overhead.
-  Error response bodies now support XML in addition to JSON. In
   addition, the HTTPError serialization code was refactored to make it
   easier to implement a custom error serializer.
-  A new method, "set\_error\_serializer" was added to falcon.API. You
   can use this method to override Falcon's default HTTPError serializer
   if you need to support custom media types.
-  Falcon's testing base class, testing.TestBase was improved to
   facilitate Py3k testing. Notably, TestBase.simulate\_request now
   takes an additional "decode" kwarg that can be used to automatically
   decode byte-string PEP-3333 response bodies.
-  An "add\_link" method was added to the Response class. Apps can use
   this method to add one or more Link header values to a response.
-  Added two new properties, req.host and req.subdomain, to make it
   easier to get at the hostname info in the request.
-  Allow a wider variety of characters to be used in query string
   params.
-  Internal APIs have been refactored to allow overriding the default
   routing mechanism. Further modularization is planned for the next
   release (0.3).
-  Changed req.get\_param so that it behaves the same whether a list was
   specified in the query string using the HTML form style (in which
   each element is listed in a separate 'key=val' field) or in the more
   compact API style (in which each element is comma-separated and
   assigned to a single param instance, as in 'key=val1,val2,val3')
-  Added a convenience method, set\_stream(...), to the Response class
   for setting the stream and its length at the same time, which should
   help people not forget to set both (and save a few keystrokes along
   the way).
-  Added several new error classes, including HTTPRequestEntityTooLarge,
   HTTPInvalidParam, HTTPMissingParam, HTTPInvalidHeader and
   HTTPMissingHeader.
-  Python 3.4 is now fully supported.
-  Various minor performance improvements

Breaking Changes
----------------

-  The deprecated util.misc.percent\_escape and
   util.misc.percent\_unescape functions were removed. Please use the
   functions in the util.uri module instead.
-  The deprecated function, API.set\_default\_route, was removed. Please
   use sinks instead.
-  HTTPRangeNotSatisfiable no longer accepts a media\_type parameter.
-  When using the comma-delimited list convention,
   req.get\_param\_as\_list(...) will no longer insert placeholders,
   using the None type, for empty elements. For example, where
   previously the query string "foo=1,,3" would result in ['1', None,
   '3'], it will now result in ['1', '3'].

Fixed
-----

-  Ensure 100% test coverage and fix any bugs identified in the process.
-  Fix not recognizing the "bytes=" prefix in Range headers.
-  Make HTTPNotFound and HTTPMethodNotAllowed fully compliant, according
   to RFC 7231.
-  Fixed the default on\_options responder causing a Cython type error.
-  URI template strings can now be of type unicode under Python 2.
-  When SCRIPT\_NAME is not present in the WSGI environ, return an empty
   string for the req.app property.
-  Global "after" hooks will now be executed even when a responder
   raises an error.
-  Fixed several minor issues regarding testing.create\_environ(...)
-  Work around a wsgiref quirk, where if no content-length header is
   submitted by the client, wsgiref will set the value of that header to
   an empty string in the WSGI environ.
-  Resolved an issue causing several source files to not be Cythonized.
-  Docstrings have been edited for clarity and correctness.

0.1.10
======

Fixed
-----

-  SCRIPT\_NAME may not always be present in the WSGI environment, so
   treat it as an empty string if not present.

0.1.9
=====

Fixed
-----

-  Addressed style issues reported by the latest pyflakes version
-  Fixed body not being decoded from UTF-8 in HTTPError tests
-  Remove unnecessary ordereddict requirement on Python 2.6

0.1.8
=====

Breaking Changes
----------------

-  srmock.headers have been normalized such that header names are always
   lowercase. This was done to make tests that rely on srmock less
   fragile.
-  Falcon now sends response headers as all lower-case ala node.js. This
   will not break well-behaved clients, since HTTP specifies that header
   names are case-insensitive.
-  The 'scheme' argument to HTTPUnauthorized can no longer be passed
   positionally; it must be a named argument.
-  You can no longer overload a single resource class to respond to
   multiple routes that differ by URI template params. This has come to
   be viewed as an anti-pattern, and so it will no longer be supported.
   If you attempt to have a single ``OxResource`` that you try to
   overload to respond to both, e.g., ``PUT /oxen/old-ben`` and
   ``GET /oxen``, it will no longer work. Developers should be advised
   to resist the temptation to overload their resources; instead, create
   multiple resources, i.e., ``OxResource`` and ``OxenResource``. It is
   common to put these two classes in the same module.

Fixed
-----

-  srmock.headers\_dict is now implemented using a case-insensitive dict
-  Per RFC 3986, Falcon now decodes escaped characters in the query
   string, plus convert '+' -> ' '. Also, Falcon now decodes multi-byte
   UTF-8 sequences after they have been unescaped.

New
---

-  Custom error handlers can be registered via a new
   API.add\_error\_handler method. You can use this to DRY your error
   handling logic by registering handlers that will get called whenever
   a given exception type is raised.
-  Support for "request sinks" was added to falcon.API. If no route
   matches a request, but the path in the requested URI matches a given
   prefix, Falcon will pass control to the given sink, regardless of the
   HTTP method requested.
-  uri module added to falcon.util which includes utilities for encoding
   and decoding URIs, as well as parsing a query string into a dict.
   This methods are more robust and more performant than their
   counterparts in urllib.
-  Subsequent calls to req.uri are now faster since the property now
   clones a cached dict instead of building a new one from scratch each
   time.
-  falcon.util now includes a case-insensitive dict borrowed from the
   Requests library. It isn't particularly fast, but is there in case
   you want to use it for anything.
-  Misc. performance optimizations to offset the impact of supporting
   case-sensitive headers and rigorous URI encoding/decoding.
-  Py33 performance improvements

0.1.7
=====

Breaking Changes
----------------

-  req.get\_params\_as\_list now inserts None as a placeholder for
   missing elements, and returns None all by itself if the param is
   present in the query string, but has an empty string as its value.
   (kgriffs)

Fixed
-----

-  req.client\_accepts does not handle media type ranges. (kgriffs)
-  req.stream semantics must be special-cased based on WSGI server.
   (kgriffs)

New
---

-  A default (catch-all) route can now be set, to provide a resource for
   handling requests that would otherwise result in a 404 status code
   being returned to the client. This feature is esp. useful when
   implementing reverse proxies with Falcon. See also
   falcon.API.set\_default\_route(). (lichray)
-  OPTIONS method requests are now automatically handled based on the
   responders defined by the resources attached to the target route.
   (lichray)
-  Responders can now use the req.headers property to obtain a copy of
   all headers received from the client. Useful for custom header
   parsing and/or request forwarding. (lichray)
-  Query param names may now contain dots. (sorenh)
-  Falcon no longer warns about Cython when installing under PyPy.
   (cabrera)
-  A client's preferred media type can be determined via a new method,
   req.client\_prefers(). (kgriffs)
-  util.to\_query\_str now recognizes lists, and serializes them as a
   comma- delimited list, passing each element through str(). (kgriffs)

0.1.6.post3
===========

Fixed
-----

-  Content-Length is now calculated correctly for Unicode bodies
   (flaper87)
-  Status code 500 is now returned for type errors raised within
   responders, even when wrapped by several hooks.

0.1.6.post2
===========

Fixed
-----

-  testtools is no longer a required dependency (cabrera)

New
---

-  Add HTTPNotAcceptable for responding with HTTP status code 406
   (lichray)
-  Add HTTPLenghRequired for responding with HTTP status code 411
   (cabrera)
-  Add generic req.client\_accepts() method (lichray)

0.1.6
=====

Fixed
-----

-  Don't percent-escape common query chars!

0.1.5
=====

Fixed
-----

-  Unicode characters in HTTPError body strings are now encoded properly
   to UTF-8.
-  Unicode characters in resp.location and resp.content\_location now
   are now percent-escaped.
-  Tox environments no longer issue warnings/errors re incompatible
   cythoned files.

New
---

-  req.get\_param and friends now accepts an optional param, "store",
   that takes a dict-like object. The value for the specified param, if
   found, will be inserted into the store, i.e., store[param] = value.
   Useful for building up kwargs.
-  req.get\_param\_as\_bool now accepts capitalized booleans as well as
   'yes' and 'no'.
-  Extended "falcon-ext" benchmark added to falcon-bench for testing
   more taxing, wost-case requests.
-  cProfile enabled for tests.
-  cProfile option added to falcon-bench.
-  Experimental memory profiling added to falcon-bench.
-  py3kwarn env added to tox (run manually).

0.1.4
=====

Fixed
-----

-  req.path now strips trailing slashes in keeping with the design
   decision in 0.1.2 to abstract those away from the app.

0.1.3
=====

Fixed
-----

-  Moved property descriptions out of class docstrings into the property
   docstrings themselves so they show up in help().
-  on\_\* responder methods in a resource class must define all URI
   template field names for any route attached to that resource. If they
   do not, Falcon will return "405 Method not allowed". This lets you
   add multiple routes to the same resource, in order to serve, for
   example, POST requests to "/super" and GET requests to
   "/super/{name}". In this example, a POST request to "/super/man"
   would result in a 405 response to the client, since the responder
   method does not define a "name" argument.

Breaking Changes
----------------

-  req.date now returns a datetime instance, and raises HTTPBadRequest
   if the value of the Date header does not conform to RFC 1123.
-  Query string parsing is now a little stricter regarding what kinds of
   field names it will accept. Generally, you will be safe if you stick
   with letters, numbers, dashes, and/or underscores.
-  Header and query parsing is more strict now. Instead of returning
   None when a value cannot be parsed, Request will raise
   HTTPBadRequest.

New
---

-  Added min and max arguments to req.get\_param\_as\_int() to help with
   input validation.
-  Added transform argument to req.get\_param\_as\_list for supplying a
   converter function for list elements.
-  Added req.get\_param\_as\_bool() for automagically converting from
   "true" and "false" to True and False, respectively.
-  Added the req.relative\_uri property which will return app + path +
   query string.
-  Added falcon.to\_query\_str() to provide an optimized query string
   generator that apps can use when generating href's.
-  Improved performance when no query string is present in the request
   URI.

0.1.2
=====

Fixed
-----

-  Falcon requires QUERY\_STRING in WSGI environ, but PEP-333 does not
   require it
-  Hook decorators can overwrite each other's actions
-  Test coverage is not 100% when branch coverage is enabled

Breaking Changes
----------------

-  Renamed falcon.testing.TestSuite to TestBase
-  Renamed TestBase.prepare hook to TestBase.before

New
---

-  Python 2.6 support
-  Added TestBase.after hook
-  Made testtools dependency optional (falls back to unittest if import
   fails)
-  Trailing slashes in routes and request paths are ignored, so you no
   longer need to add two routes for each resource

0.1.1
=====

Fixed
-----

-  Falcon won't install on a clean system
-  Multiple headers possible in the HTTP response
-  testing.create\_environ not setting all PEP-3333 vars
-  testing.StartRequestMock does not accept exc\_info per PEP-3333
-  Tests not at 100% code coverage

New
---

-  Hooks: falcon.before and falcon.after decorators can apply hooks to
   entire resources and/or individual methods. Hooks may also be
   attached globally by passing them into the falcon.API initializer.
-  Common request and response headers can now be accessed as
   attributes, e.g. "req.content\_length" and "resp.etag".
-  Cython: On installation, Falcon will now compile itself with Cython
   when available. This boosts the framework's performance by ~20%.
-  PyPy and Python 3.3 support
-  Vastly improved docstrings

0.1.0
=====

Initial release.
