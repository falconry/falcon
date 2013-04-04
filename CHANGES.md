# v0.1.3 #

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

# v0.1.2 #

## Fixed ##

* Falcon requires QUERY_STRING in WSGI environ, but PEP-333 does not require it
* Hook decorators can overwrite eachother's actions
* Test coverage is not 100% when branch coverage is enabled

## Breaking Changes ##

* Renamed falcon.testing.TestSuite to TestBase
* Renamed TestBase.prepare hook to TestBase.before

## New ##

* Python 2.6 support
* Added TestBase.after hook
* Made testtools dependency optional (falls back to unittest if import fails)
* Trailing slashes in routes and request paths are ignored, so you no longer need to add two routes for each resource

# v0.1.1 #

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

# v0.1.0 #

Initial release.