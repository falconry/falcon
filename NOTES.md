* Keep-Alive is intentially disabled for HTTP/1.0 clients to mitigate problems with proxies. See also http://tools.ietf.org/html/rfc2616#section-19.6.2
* resp.set_header assumes second param is a string. App may crash otherwise. 
* If you have several headers to set, consider using set_headers to avoid function call overhead
* Don't set content-length. It will only be overridden.
* Header names are case-insensitive in req.get_header
* Set body to a byte string, as per PEP 333 - http://www.python.org/dev/peps/pep-0333/#unicode-issues - if it is textual, it's up to the app to set the proper media type
* If both body and stream are set, body will be used
* For streaming large items, assign a generator to resp.stream that yields data in reasonable chunk sizes (what's a reasonable size?). Falcon will then leave off the Content-Length header, and hopefully your WSGI server will do the right thing, assuming you've told it to enable keep-alive (PEP-333 prohibits apps from setting hop-by-hop headers itself, such as Transfer-Encoding).
  * If you know the size of the stream in advance, set stream\_len and Falcon will use it to set Content-Length, avoiding the whole chunked encoding issue altogether. 


