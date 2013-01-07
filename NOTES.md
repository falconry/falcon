* Falcon doesn't officially support Python 3; it's on our TODO list.
* Falcon is based on byte strings, and does no conversions to UTF-16 (for example). If your app needs to use wide strings, you'll need to do the conversion manually. However, we recommend just keeping everything UTF-8 to avoid writing extra code and spinning CPU cycles.
* Keep-Alive is intentially disabled for HTTP/1.0 clients to mitigate problems with proxies. See also http://tools.ietf.org/html/rfc2616#section-19.6.2
* resp.set_header assumes both params are strings. App may crash otherwise. Falcon trusts the caller. You *are* testing all your code paths, aren't you?
* If the WSGI server passes an empty path, Falcon will force it to '/', so you don't have to test for the empty string in your app.
* If you are hosting multiple apps with a single WSGI server, the SCRIPT_NAME variable can read from req.app
* If you have several headers to set, consider using set_headers to avoid function call overhead
* Don't set content-length. It will only be overridden.
* The order in which header fields are sent in the response is undefined. Headers are not grouped according to the recommendation in [RFC 2616](http://tools.ietf.org/html/rfc2616#section-4.2) in order to generate responses as quickly as possible.
* Header names are case-insensitive in req.get_header
* Set body to a byte string, as per PEP 333 - http://www.python.org/dev/peps/pep-0333/#unicode-issues - if it is textual, it's up to the app to set the proper media type
* If both body and stream are set, body will be used
* For streaming large items, assign a generator to resp.stream that yields data in reasonable chunk sizes (what's a reasonable size?). Falcon will then leave off the Content-Length header, and hopefully your WSGI server will do the right thing, assuming you've told it to enable keep-alive (PEP-333 prohibits apps from setting hop-by-hop headers itself, such as Transfer-Encoding).
  * If you know the size of the stream in advance, set stream\_len and Falcon will use it to set Content-Length, avoiding the whole chunked encoding issue altogether. 


