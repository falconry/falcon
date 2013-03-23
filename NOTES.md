### Assumptions ###

In order to stay lean and fast, Falcon makes several assumptions.

First, Falcon assumes that resource responders will (for the most part) do the right thing. In other words, Falcon doesn't try very hard to protect responder code from itself.

This requires some discipline on the part of the developer.

1. Resource responders set response variables to sane values.
1. All code is well-tested, with high code coverage. It's not Falcon's job to babysit.
1. Anticipate and handle exceptions. Falcon only expects HTTPError exception types to be thrown from responders.

### Misc. ###

* Falcon probably isn't thread-safe, so don't try it. Run multiple worker processes, each with a non-blocking I/O loop instead.
* For 204, just set the status and no body. Falcon will ignore the body even if you set it.
* If you set resp.body to a Unicode string, Falcon will attempt to encode it as UTF-8 before sending the content to the WSGI server (as required by PEP-333). If you already have encoded data (or it's a binary blob), use resp.data instead (it's faster).
* Default media type (returned as the value of the 'Content-Type' header) for responses is 'application/json; charset=utf-8' (falcon.DEFAULT\_MEDIA\_TYPE), and the default status is '200 OK.' You can set a custom media type in the API constructor to save yourself from having to always set Content-Type for each request.
* resp.set_header assumes both params are strings. App may crash otherwise. Falcon trusts the caller. You *are* testing all your code paths, aren't you?
* If you need the protocol (http vs https) to construct hrefs in your responses (hypermedia is good, trust me), you can get it from req.scheme
* URI template and query string field names must include only ASCII a-z, A-Z, and the underscore '_' character. Try it; you'll like it. This simplifies parsing and helps speed things up a bit.
* on_* responder methods in a resource class must define all URI template field names for any route attached to that resource. If they do not, Falcon will return "405 Method not allowed". This allows you to add multiple routes to the same resource, in order to serve, for example, POST requests to "/super" and GET requests to "/super/{name}". In this example, a POST request to "/super/"
* Query params must have a value. In other words, 'foo' or 'foo=' will result in the parameter being ignored.
* If the WSGI server passes an empty path, Falcon will force it to '/', so you don't have to test for the empty string in your app.
* The routes '/foo/bar' and '/foo/bar/' are identical as far as Falcon is concerned. Requests coming in for either will be sent to the same resource.
* If you are hosting multiple apps with a single WSGI server, the SCRIPT_NAME variable can be read from req.app
* If you have several headers to set, consider using set_headers to avoid function call overhead
* Don't set content-length. It will only be overridden.
* The order in which header fields are sent in the response is undefined. Headers are not grouped according to the recommendation in [RFC 2616](http://tools.ietf.org/html/rfc2616#section-4.2) in order to generate responses as quickly as possible.
* Header names are case-insensitive in req.get_header
* For streaming large items, assign a generator or IO object to resp.stream. If you know the file size in advance, assign it to stream\_len. For dynamically-generated content, leave off stream\_len, and Falcon will then leave off the Content-Length header, and hopefully your WSGI server will do the right thing, assuming you've told it to enable keep-alive (PEP-333 prohibits apps from setting hop-by-hop headers itself, such as Transfer-Encoding).


