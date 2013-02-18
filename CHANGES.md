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