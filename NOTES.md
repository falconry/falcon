### Assumptions ###

In order to stay lean and fast, Falcon makes several assumptions.

First, Falcon assumes that resource responders will (for the most part) do the right thing. In other words, Falcon doesn't try very hard to protect responder code from itself. 

This requires some discipline on the part of the developer.

1. Resource responders set response variables to sane values.
1. All code is well-tested, with high code coverage. It's not Falcon's job to babysit.
1. Anticipate and handle exceptions. Falcon only expects HTTPError exception types to be thrown from responders.

### Misc. ###

* Falcon probably isn't thread-safe, so don't try it. Run multiple worker processes, each with a non-blocking I/O loop instead.
* Falcon doesn't officially support Python 3; it's on our TODO list.
* Falcon is based on byte strings (str in Python 2, bytes in Python 3), and does no conversions to UTF-16 (for example). If your app needs to use wide strings, you'll need to do the conversion manually. However, we recommend just keeping everything UTF-8 as much as possible for efficiency's sake.
* resp.set_header assumes both params are strings. App may crash otherwise. Falcon trusts the caller. You *are* testing all your code paths, aren't you?
* If you need the protocol (http vs https) to construct hrefs in your responses (hypermedia is good, trust me), you can get it from req.scheme
* URI template and query string field names must include only ASCII a-z, A-Z, and the underscore '_' character. Try it; you'll like it. This simplifies parsing and helps speed things up a bit. 
* Query params must have a value. In other words, 'foo' or 'foo=' will result in the parameter being ignored.
* If the WSGI server passes an empty path, Falcon will force it to '/', so you don't have to test for the empty string in your app.
* If you are hosting multiple apps with a single WSGI server, the SCRIPT_NAME variable can read from req.app
* If you have several headers to set, consider using set_headers to avoid function call overhead
* Don't set content-length. It will only be overridden.
* The order in which header fields are sent in the response is undefined. Headers are not grouped according to the recommendation in [RFC 2616](http://tools.ietf.org/html/rfc2616#section-4.2) in order to generate responses as quickly as possible.
* Header names are case-insensitive in req.get_header
* Set body to a byte string, as per PEP 333 - http://www.python.org/dev/peps/pep-0333/#unicode-issues - if it is textual, it's up to the app to set the proper media type
* For streaming large items, assign a generator or IO object to resp.stream. If you know the file size in advance, assign it to stream\_len. For dynamically-generated content, leave off stream\_len, and Falcon will then leave off the Content-Length header, and hopefully your WSGI server will do the right thing, assuming you've told it to enable keep-alive (PEP-333 prohibits apps from setting hop-by-hop headers itself, such as Transfer-Encoding).


