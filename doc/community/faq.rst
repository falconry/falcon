.. _faq:

Questions & Answers
===================

How do I use WSGI middleware with Falcon?
----

Instances of `falcon.API` are first-class WSGI apps, so you can use the
standard pattern outlined in PEP-3333. In your main "app" file, you would
simply wrap your api instance with a middleware app. For example:

.. code:: python

    import my_restful_service
    import some_middleware

    app = some_middleware.DoSomethingFancy(my_restful_service.api)

See also the `WSGI middleware example <http://legacy.python.org/dev/peps/pep-3333/#middleware-components-that-play-both-sides>`_ given in PEP-3333. Note that use of Paste for wiring up
middleware is discouraged these days, because that package is not
well-maintained, and is incompatible with Python 3.


Why doesn't Falcon include X?
----
The Falcon framework lets you decide your own answers to questions like:

* JSON or MessagePack?
* konval or jsonschema?
* Mongothon or Monk?
* Storm, SQLAlchemy or peewee?
* Jinja or Tenjin?
* python-multipart or cgi.FieldStorage?
* gevent or eventlet?

The Python ecosytem offers a bunch of great libraries that you
are welcome to use from within your responders and hooks.
Falcon doesn't try to dictate what you should use, since that would take
away your freedom to choose the best tool for the job.

How do I authenticate requests?
----
You can use a *before* hook to authenticate and authorize requests. Hooks
have full access to the Request and Response objects.

.. code:: python

    def auth(req, resp, params):
        token = req.get_header('X-Auth-Token')

        if token is None:
            description = ('Please provide an auth token '
                           'as part of the request.')

            raise falcon.HTTPUnauthorized('Auth token required',
                                          description,
                                          href='http://docs.example.com/auth')

        if not token_is_valid(token, params['user_id']):
            description = ('The provided auth token is not valid. '
                           'Please request a new token and try again.')

            raise falcon.HTTPUnauthorized('Authentication required',
                                          description,
                                          href='http://docs.example.com/auth',
                                          scheme='Token; UUID')

        authorized_projects = get_projects(token)
        project = req.get_header('X-Project-ID')

        if project not in authorized_projects:
            description = 'The requested project ID could not be found.'
            raise falcon.HTTPForbidden('Unknown Project ID',
                                        description,
                                        href='http://docs.example.com/headers')

Is Falcon thread-safe?
----

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

Why doesn't Falcon create a new Resource instance for every request?
----
Falcon generally tries to minimize the number of objects that it
instantiates. It does this for two reasons: first, to avoid the expense of
creating the object, and second to mitigate memory fragmentation.

Therefore, when adding a route, Falcon requires an *instance* of your
resource class, rather than the class type. That same instance will be used
to server all requests coming in on that route.

How do I implement both POSTing and GETing items for the same resource?
----
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
out to make routing definitions more complicated/less intuitive.

See also :ref:`this section of the tutorial <tutorial-serving-images>`.

How can I pass data from a hook to a responder, and between hooks?
----
You can inject extra responder kwargs from a hook by adding them
to the *params* dict passed into the hook. You can also add custom data to
the req.env WSGI dict, as a way of passing contextual information around.

.. note::
    Falcon 0.2 will add a "context" dict to Request to provide a cleaner
    alternative to using req.env.

Does Falcon set Content-Length or do I need to do that explicitly?
----

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
----

Falcon skips processing the response body to save a few cycles when the HTTP
spec defines that the response should *have* no body. First, if the client
sends a HEAD request, the response body will be empty. Second, if the response
status set by a resource is one of the following, Falcon will skip processing
the response body::

    falcon.HTTP_100
    falcon.HTTP_204
    falcon.HTTP_416
    falcon.HTTP_304

Why does raising an error inside a resource crash my app?
----

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
----

Falcon normalizes incoming URI paths to simplify later processing and
improve the predictability of application logic. In addition to stripping
a trailing slashes, if any, Falcon will convert empty paths to '/'.

Note also that routing is also normalized, so adding a route for '/foo/bar'
also implicitly adds a route for '/foo/bar/'. Requests coming in for either
path will be sent to the same resource.

Why are field names in URI templates restricted to certain characters?
----

Field names are restricted to the ASCII characters a-z, A-Z, and '_'. Using a
restricted set of characters reduces the overhead of parsing incoming
requests.

Why is my query parameter missing from the req object?
----

If a query params does not have a value, Falcon will treat it as though the
param were omitted completely from the URI. For example, 'foo' or 'foo=' will
result in the parameter being ignored.

Is there a way for me to ensure headers are sent to clients in a specific order?
----

In order to generate HTTP responses as quickly as possible, Falcon does not
try to sort or even logically group related headers in the HTTP response.

.. If Falcon is designed for building web APIs, why does it support forms?
.. ----
.. Doesn't support files, allows same code to handle both...