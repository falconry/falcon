* Keep-Alive is intentially disabled for HTTP/1.0 clients to mitigate problems with proxies. See also http://tools.ietf.org/html/rfc2616#section-19.6.2
* Header names are case-insensitive in req.get_header
* Set body to a byte string, as per PEP 333 - http://www.python.org/dev/peps/pep-0333/#unicode-issues - if it is textual, it's up to the app to set the proper media type
* If both body and stream are set, body will be used
* For streaming large items, assign a generator to resp.stream that yields data in reasonable chunk sizes (what's a reasonable size?). If stream is set, Falcon will assume Transfer-Encoding: chunked unless you specify stream_len, in which case Falcon will set Content-Length to stream_len. Be sure stream_len is accurate; if you lie about it, then clients and possibly your WSGI server) will hang until the connection times out, waiting for stream to generate enough data.


