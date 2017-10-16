.. _faq:

FAQ
===

.. contents:: :local:

Why doesn't Falcon come with batteries included?
------------------------------------------------
Falcon is designed for applications that require a high level of
customization or performance tuning. The framework's minimalist design
frees the developer to select the best strategies and 3rd-party
packages for the task at hand.

The Python ecosystem offers a number of great packages that you can
use from within your responders, hooks, and middleware components. As
a starting point, the community maintains a list of `Falcon add-ons
and complementary packages <https://github.com/falconry/falcon/wiki>`_.

How do I use WSGI middleware with Falcon?
-----------------------------------------
Instances of `falcon.API` are first-class WSGI apps, so you can use the
standard pattern outlined in PEP-3333. In your main "app" file, you would
simply wrap your api instance with a middleware app. For example:

.. code:: python

    import my_restful_service
    import some_middleware

    app = some_middleware.DoSomethingFancy(my_restful_service.api)

See also the `WSGI middleware example <http://legacy.python.org/dev/peps/pep-3333/#middleware-components-that-play-both-sides>`_ given in PEP-3333.


How do I authenticate requests?
-------------------------------
Hooks and middleware components can be used together to authenticate and
authorize requests. For example, a middleware component could be used to
parse incoming credentials and place the results in ``req.context``.
Downstream components or hooks could then use this information to
authorize the request, taking into account the user's role and the requested
resource.


Why doesn't Falcon create a new Resource instance for every request?
--------------------------------------------------------------------
Falcon generally tries to minimize the number of objects that it
instantiates. It does this for two reasons: first, to avoid the expense of
creating the object, and second to reduce memory usage. Therefore, when
adding a route, Falcon requires an *instance* of your resource class, rather
than the class type. That same instance will be used to serve all requests
coming in on that route.


Is Falcon thread-safe?
----------------------
New Request and Response objects are created for each incoming HTTP request.
However, a single instance of each resource class attached to a route is
shared among all requests. Therefore, as long as you are careful about the
way responders access class member variables to avoid conflicts, your
WSGI app should be thread-safe.

That being said, Falcon-based services are usually deployed using green
threads (via the gevent library or similar) which aren't truly running
concurrently, so there may be some edge cases where Falcon is not
thread-safe that haven't been discovered yet.

*Caveat emptor!*


How do I implement both POSTing and GETing items for the same resource?
-----------------------------------------------------------------------
Suppose you wanted to implement the following endpoints::

    # Resource Collection
    POST /resources
    GET /resources{?marker, limit}

    # Resource Item
    GET /resources/{id}
    PATCH /resources/{id}
    DELETE /resources/{id}

You can implement this sort of API by simply using two Python classes, one
to represent a single resource, and another to represent the collection of
said resources. It is common to place both classes in the same module.

The Falcon community did some experimenting with routing both singleton
and collection-based operations to the same Python class, but it turned
out to make routing definitions more complicated and less intuitive. That
being said, we are always open to new ideas, so please let us know if you
discover another way.

See also :ref:`this section of the tutorial <tutorial-serving-images>`.


How can I pass data from a hook to a responder, and between hooks?
------------------------------------------------------------------
You can inject extra responder kwargs from a hook by adding them
to the *params* dict passed into the hook. You can also add custom data to
the ``req.context`` dict, as a way of passing contextual information around.


Does Falcon set Content-Length or do I need to do that explicitly?
------------------------------------------------------------------
Falcon will try to do this for you, based on the value of `resp.body`,
`resp.data`, or `resp.stream_len` (whichever is set in the response, checked
in that order.)

For dynamically-generated content, you can choose to leave off `stream_len`,
in which case Falcon will then leave off the Content-Length header, and
hopefully your WSGI server will do the Right Thing™ (assuming you've told
it to enable keep-alive).

.. note:: PEP-333 prohibits apps from setting hop-by-hop headers itself,
    such as Transfer-Encoding.


I'm setting a response body, but it isn't getting returned. What's going on?
----------------------------------------------------------------------------
Falcon skips processing the response body when, according to the HTTP
spec, no body should be returned. If the client
sends a HEAD request, the framework will always return an empty body.
Falcon will also return an empty body whenever the response status is any
of the following::

    falcon.HTTP_100
    falcon.HTTP_204
    falcon.HTTP_416
    falcon.HTTP_304

If you have another case where you body isn't being returned to the
client, it's probably a bug! Let us know in IRC or on the mailing list so
we can help.


My app is setting a cookie, but it isn't being passed back in subsequent requests.
----------------------------------------------------------------------------------
By default, Falcon enables the `secure` cookie attribute. Therefore, if you are
testing your app over HTTP (instead of HTTPS), the client will not send the
cookie in subsequent requests. See also :ref:`the cookie documentation <cookie-secure-attribute>`


Why does raising an error inside a resource crash my app?
---------------------------------------------------------
Generally speaking, Falcon assumes that resource responders (such as *on_get*,
*on_post*, etc.) will, for the most part, do the right thing. In other words,
Falcon doesn't try very hard to protect responder code from itself.

This approach reduces the number of (often) extraneous checks that Falcon
would otherwise have to perform, making the framework more efficient. With
that in mind, writing a high-quality API based on Falcon requires that:

#. Resource responders set response variables to sane values.
#. Your code is well-tested, with high code coverage.
#. Errors are anticipated, detected, and handled appropriately within
   each responder and with the aid of custom error handlers.

.. tip:: Falcon will re-raise errors that do not inherit from
    ``falcon.HTTPError`` unless you have registered a custom error
    handler for that type (see also: :ref:`falcon.API <api>`).


Why are trailing slashes trimmed from req.path?
-----------------------------------------------
Falcon normalizes incoming URI paths to simplify later processing and
improve the predictability of application logic. In addition to stripping
a trailing slashes, if any, Falcon will convert empty paths to "/".

Note also that routing is also normalized, so adding a route for "/foo/bar"
also implicitly adds a route for "/foo/bar/". Requests coming in for either
path will be sent to the same resource.


Why are field names in URI templates restricted to certain characters?
----------------------------------------------------------------------
Field names are restricted to the ASCII characters in the set ``[a-zA-Z_]``.
Using a restricted set of characters allows the framework to make
simplifying assumptions that reduce the overhead of parsing incoming requests.


Why is my query parameter missing from the req object?
------------------------------------------------------
If a query param does not have a value, Falcon will by default ignore that
parameter. For example, passing 'foo' or 'foo=' will result in the parameter
being ignored.

If you would like to recognize such parameters, you must set the
`keep_blank_qs_values` request option to ``True``. Request options are set
globally for each instance of ``falcon.API`` through the `req_options`
attribute. For example:

.. code:: python

    api.req_options.keep_blank_qs_values = True


How can I access POSTed form params?
------------------------------------
By default, Falcon does not consume request bodies. However, setting
the :attr:`~RequestOptions.auto_parse_form_urlencoded` to ``True``
on an instance of ``falcon.API``
will cause the framework to consume the request body when the
content type is `application/x-www-form-urlencoded`, making
the form parameters accessible via :attr:`~.Request.params`,
:meth:`~.Request.get_param`, etc.

.. code:: python

    api.req_options.auto_parse_form_urlencoded = True

Alternatively, POSTed form parameters may be read directly from
:attr:`~.Request.stream` and parsed via
:meth:`falcon.uri.parse_query_string` or
`urllib.parse.parse_qs() <https://docs.python.org/3.6/library/urllib.parse.html#urllib.parse.parse_qs>`_.


How can I access POSTed files?
------------------------------
Falcon does not currently support parsing files submitted by
an HTTP form (``multipart/form-data``), although we do plan
to add this feature in a future version. In the meantime,
you can use the standard ``cgi.FieldStorage`` class to
parse the request:

.. code:: python

    # TODO: Either validate that content type is multipart/form-data
    # here, or in another hook before allowing execution to proceed.

    # This must be done to avoid a bug in cgi.FieldStorage
    env = req.env
    env.setdefault('QUERY_STRING', '')

    # TODO: Add error handling, when the request is not formatted
    # correctly or does not contain the desired field...

    # TODO: Consider overriding make_file, so that you can
    # stream directly to the destination rather than
    # buffering using TemporaryFile (see http://goo.gl/Yo8h3P)
    form = cgi.FieldStorage(fp=req.stream, environ=env)

    file_item = form[name]
    if file_item.file:
        # TODO: It's an uploaded file... read it in
    else:
        # TODO: Raise an error

You might also try this `streaming_form_data <https://streaming-form-data.readthedocs.io/en/latest/>`_ package by Siddhant Goel.


How do I consume a query string that has a JSON value?
------------------------------------------------------
Falcon defaults to treating commas in a query string as literal characters
delimiting a comma separated list. For example, given
the query string ``?c=1,2,3``, Falcon defaults to adding this to your
``request.params`` dictionary as ``{'c': ['1', '2', '3']}``. If you attempt
to use JSON in the value of the query string, for example ``?c={'a':1,'b':2}``,
the value will get added to your ``request.params`` in a way that you probably
don't expect: ``{'c': ["{'a':1", "'b':2}"]}``.

Commas are a reserved character that can be escaped according to
`RFC 3986 - 2.2. Reserved Characters <https://tools.ietf.org/html/rfc3986#section-2.2>`_,
so one possible solution is to percent encode any commas that appear in your
JSON query string. The other option is to switch the way Falcon
handles commas in a query string by setting the
:attr:`~RequestOptions.auto_parse_qs_csv` to ``False`` on an instance of
``falcon.API``. For example:

.. code:: python

    api.auto_parse_qs_csv = False

When :attr:`~RequestOptions.auto_parse_qs_csv` is set to ``False``, the
value of the query string ``?c={'a':1,'b':2}`` will be added to
your ``request.params`` dictionary as  ``{'c': "{'a':1,'b':2}"}``.
This lets you consume JSON whether or not the client chooses to escape
commas in the request.


How do I generate API documentation for my Falcon API?
------------------------------------------------------
When it comes to API documentation, some developers prefer to use the API
implementation as the user contract or source of truth (taking an
implementation-first approach), while other developers prefer to use the API
spec itself as the contract, implementing and testing the API against that spec
(taking a design-first approach).

At the risk of erring on the side of flexiblity, Falcon does not provide API
spec support out of the box. However, there are several community projects
available in this vein. Our
`Add on Catalog <https://github.com/falconry/falcon/wiki/Add-on-Catalog>`_ lists
a couple of these projects, but you may also wish to search
`PyPI <https://pypi.python.org/pypi>`_ for additional packages.

If you are interested in the design-first approach mentioned above, you may
also want to check out API design and gateway services such as Tyk, Apiary,
Amazon API Gateway, or Google Cloud Endpoints.


How do you write a custom handler for 404 and 500 pages in falcon?
------------------------------------------------------------------
When a route can not be found for an incoming request, Falcon uses a default
responder that simply raises an instance of :attr:`falcon.HTTPNotFound`. You
can use :meth:`falcon.API.add_error_handler` to register a custom error handler
for this exception type. Alternatively, you may be able to configure your web
server to transform the response (e.g., using Nginx's ``error_page``
directive).

500 errors are typically the result of an unhandled exception making its way
up to the web server. To handle these errors more gracefully, you can add a
custom error handler for Python's base `Exception` type.


How can I serve a downloadable file with falcon?
------------------------------------------------
In the ``on_get()`` responder method for the resource, you can tell the user
agent to download the file by setting the Content-Disposition header. For
example:

.. code:: python

    resp.set_header('Content-Disposition', 'attachment; filename="something.zip"')
