# 0.1.9 #

## Fixed ##

* Addressed style issues reported by the latest pyflakes version
* Fixed body not being decoded from UTF-8 in HTTPError tests
* Remove unnecessary ordereddict requirement on Python 2.6

# 0.1.8 #

## Breaking Changes ##

* srmock.headers have been normalized such that header names are always
lowercase. This was done to make tests that rely on srmock less
fragile.
* Falcon now sends response headers as all lower-case ala node.js. This
will not break well-behaved clients, since HTTP specifies that header
names are case-insensitive.
* The 'scheme' argument to HTTPUnauthorized can no longer be passed
positionally; it must be a named argument.
* You can no longer overload a single resource class to respond to multiple
routes that differ by URI template params. This has come to be viewed as an
anti-pattern, and so it will no longer be supported. If you attempt to have
a single `OxResource` that you try to overload to respond to both, e.g.,
`PUT /oxen/old-ben` and `GET /oxen`, it will no longer work. Developers
should be advised to resist the temptation to overload their resources;
instead, create multiple resources, i.e., `OxResource` and `OxenResource`.
It is common to put these two classes in the same module.

## Fixed ##

* srmock.headers_dict is now implemented using a case-insensitive dict
* Per RFC 3986, Falcon now decodes escaped characters in the query
string, plus convert '+' -> ' '. Also, Falcon now decodes multi-byte
UTF-8 sequences after they have been unescaped.

## New ##

* Custom error handlers can be registered via a new API.add_error_handler
method. You can use this to DRY your error handling logic by registering
handlers that will get called whenever a given exception type is raised.
* Support for "request sinks" was added to falcon.API. If no route matches
a request, but the path in the requested URI matches a given prefix,
Falcon will pass control to the given sink, regardless of the HTTP method
requested.
* uri module added to falcon.util which includes utilities for encoding
and decoding URIs, as well as parsing a query string into a dict. This
methods are more robust and more performant than their counterparts in
urllib.
* Subsequent calls to req.uri are now faster since the property now
clones a cached dict instead of building a new one from scratch each time.
* falcon.util now includes a case-insensitive dict borrowed from
the Requests library. It isn't particularly fast, but is there in
case you want to use it for anything.
* Misc. performance optimizations to offset the impact of supporting
case-sensitive headers and rigorous URI encoding/decoding.
* Py33 performance improvements

# 0.1.7 #

## Breaking Changes ##

* req.get_params_as_list now inserts None as a placeholder for missing
elements, and returns None all by itself if the param is present in the
query string, but has an empty string as its value. (kgriffs)

## Fixed ##

* req.client_accepts does not handle media type ranges. (kgriffs)
* req.stream semantics must be special-cased based on WSGI server. (kgriffs)

## New ##

* A default (catch-all) route can now be set, to provide a resource for
handling requests that would otherwise result in a 404 status code being
returned to the client. This feature is esp. useful when implementing
reverse proxies with Falcon. See also falcon.API.set_default_route(). (lichray)
* OPTIONS method requests are now automatically handled based on the
responders defined by the resources attached to the target route. (lichray)
* Responders can now use the req.headers property to obtain a copy of
all headers received from the client. Useful for custom header parsing
and/or request forwarding. (lichray)
* Query param names may now contain dots. (sorenh)
* Falcon no longer warns about Cython when installing under PyPy. (cabrera)
* A client's preferred media type can be determined via a new method,
req.client_prefers(). (kgriffs)
* util.to_query_str now recognizes lists, and serializes them as a comma-
delimited list, passing each element through str(). (kgriffs)

# 0.1.6.post3 #

## Fixed ##

* Content-Length is now calculated correctly for Unicode bodies (flaper87)
* Status code 500 is now returned for type errors raised within responders,
even when wrapped by several hooks.

# 0.1.6.post2 #

## Fixed ##

* testtools is no longer a required dependency (cabrera)

## New ##

* Add HTTPNotAcceptable for responding with HTTP status code 406 (lichray)
* Add HTTPLenghRequired for responding with HTTP status code 411 (cabrera)
* Add generic req.client_accepts() method (lichray)

# 0.1.6 #

## Fixed ##

* Don't percent-escape common query chars!

# 0.1.5 #

## Fixed ##

* Unicode characters in HTTPError body strings are now encoded properly to UTF-8.
* Unicode characters in resp.location and resp.content_location now are now percent-escaped.
* Tox environments no longer issue warnings/errors re incompatible cythoned files.

## New ##

* req.get_param and friends now accepts an optional param, "store", that takes a dict-like object. The value for the specified param, if found, will be inserted into the store, i.e., store[param] = value. Useful for building up kwargs.
* req.get_param_as_bool now accepts capitalized booleans as well as 'yes' and 'no'.
* Extended "falcon-ext" benchmark added to falcon-bench for testing more taxing, wost-case requests.
* cProfile enabled for tests.
* cProfile option added to falcon-bench.
* Experimental memory profiling added to falcon-bench.
* py3kwarn env added to tox (run manually).

# 0.1.4 #

## Fixed ##

* req.path now strips trailing slashes in keeping with the design decision in 0.1.2 to abstract those away from the app.

# 0.1.3 #

## Fixed ##

* Moved property descriptions out of class docstrings into the property docstrings themselves so they show up in help().
* on_* responder methods in a resource class must define all URI template field names for any route attached to that resource. If they do not, Falcon will return "405 Method not allowed". This lets you add multiple routes to the same resource, in order to serve, for example, POST requests to "/super" and GET requests to "/super/{name}". In this example, a POST request to "/super/man" would result in a 405 response to the client, since the responder method does not define a "name" argument.

## Breaking Changes ##

* req.date now returns a datetime instance, and raises HTTPBadRequest if the value of the Date header does not conform to RFC 1123.
* Query string parsing is now a little stricter regarding what kinds of field names it will accept. Generally, you will be safe if you stick with letters, numbers, dashes, and/or underscores.
* Header and query parsing is more strict now. Instead of returning None when a value cannot be parsed, Request will raise HTTPBadRequest.

## New ##

* Added min and max arguments to req.get_param_as_int() to help with input validation.
* Added transform argument to req.get_param_as_list for supplying a converter function for list elements.
* Added req.get_param_as_bool() for automagically converting from "true" and "false" to True and False, respectively.
* Added the req.relative_uri property which will return app + path + query string.
* Added falcon.to_query_str() to provide an optimized query string generator that apps can use when generating href's.
* Improved performance when no query string is present in the request URI.

# 0.1.2 #

## Fixed ##

* Falcon requires QUERY_STRING in WSGI environ, but PEP-333 does not require it
* Hook decorators can overwrite each other's actions
* Test coverage is not 100% when branch coverage is enabled

## Breaking Changes ##

* Renamed falcon.testing.TestSuite to TestBase
* Renamed TestBase.prepare hook to TestBase.before

## New ##

* Python 2.6 support
* Added TestBase.after hook
* Made testtools dependency optional (falls back to unittest if import fails)
* Trailing slashes in routes and request paths are ignored, so you no longer need to add two routes for each resource

# 0.1.1 #

## Fixed ##

* Falcon won't install on a clean system
* Multiple headers possible in the HTTP response
* testing.create_environ not setting all PEP-3333 vars
* testing.StartRequestMock does not accept exc_info per PEP-3333
* Tests not at 100% code coverage

## New ##

* Hooks: falcon.before and falcon.after decorators can apply hooks to entire resources and/or individual methods. Hooks may also be attached globally by passing them into the falcon.API initializer.
* Common request and response headers can now be accessed as attributes, e.g. "req.content_length" and "resp.etag".
* Cython: On installation, Falcon will now compile itself with Cython when available. This boosts the framework's performance by ~20%.
* PyPy and Python 3.3 support
* Vastly improved docstrings

# 0.1.0 #

Initial release.