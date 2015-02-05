.. _faq:

FAQ
===

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


Why doesn't Falcon include X?
-----------------------------
The Python ecosytem offers a bunch of great libraries that you
are welcome to use from within your responder, hooks, and middleware.
Falcon doesn't try to dictate what you should use, since that would take
away your freedom to choose the best tool for the job.

The Falcon framework lets you decide your own answers to questions like:

* gevent or asyncio?
* JSON or MessagePack?
* konval or jsonschema?
* Mongothon or Monk?
* Storm, SQLAlchemy or peewee?
* Jinja or Tenjin?
* python-multipart or cgi.FieldStorage?



How do I authenticate requests?
-------------------------------
Hooks and/or middleware components can be used to to authenticate and
authorize requests. For example, you could create a middleware component
that parses incoming credentials and places the result in ``req.context``.
Downstream components or hooks could then use this info to authenticate
the user, and then finally authorize the request, taking into account the
user's role and the requested resource.

.. Tip::

    The `Talons project <https://github.com/talons/talons>`_ maintains a
    collection of auth plugins for the Falcon framework.

Why doesn't Falcon create a new Resource instance for every request?
--------------------------------------------------------------------
Falcon generally tries to minimize the number of objects that it
instantiates. It does this for two reasons: first, to avoid the expense of
creating the object, and second to reduce memory usage. Therefore, when
adding a route, Falcon requires an *instance* of your resource class, rather
than the class type. That same instance will be used to server all requests
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


.. If Falcon is designed for building web APIs, why does it support forms?
.. ----
.. Doesn't support files, allows same code to handle both...