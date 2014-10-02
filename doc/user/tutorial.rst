.. _tutorial:

Tutorial
========

This page walks you through building an API for an image-sharing service. Along
the way, you will learn about Falcon's features and the terminology used by
the framework. You'll also learn how to query Falcon's docstrings, and get a
quick overview of the WSGI standard.


.. include:: big-picture-snip.rst


First Steps
-----------

Before continuing, be sure you've got Falcon :ref:`installed <install>`. Then,
create a new project folder called "look" and cd into it:

.. code:: bash

    $ mkdir look
    $ cd look

Next, let's create a new file that will be the entry point into your app:

.. code:: bash

    $ touch app.py

Open that file in your favorite text editor and add the following lines:

.. code:: python

    import falcon

    api = application = falcon.API()

That creates your WSGI application and aliases it as ``api``. You can use any
variable names you like, but we'll use ``application`` since that is what
Gunicorn expects it to be called, by default.

A WSGI application is just a callable with a well-defined signature so that
you can host the application with any web server that understands the `WSGI
protocol <http://legacy.python.org/dev/peps/pep-3333/>`_. Let's take a look
at the falcon.API class.

First, install IPython (if you don't already have it), and fire it up:

.. code:: bash

    $ pip install ipython
    $ ipython

Now, type the following to introspect the falcon.API callable:

.. code:: bash

    In [1]: import falcon

    In [2]: falcon.API.__call__?

Alternatively, you can use the built-in ``help`` function:

.. code:: bash

    In [3]: help(falcon.API.__call__)

Note the method signature. ``env`` and ``start_response`` are standard
WSGI params. Falcon adds a thin abstraction on top of these params
so you don't have to interact with them directly.

The Falcon framework contains extensive inline documentation that you can
query using the above technique. The team has worked hard to optimize
the docstrings for readability, so that you can quickly scan them and find
what you need.

.. tip::

    `bpython <http://bpython-interpreter.org/>`_ is another super-
    powered REPL that is good to have in your toolbox when
    exploring a new library.


Hosting Your App
----------------

Now that you have a simple Falcon app, you can take it for a spin with
a WSGI server. Python includes a reference server for self-hosting, but
let's use something that you would actually deploy in production.

.. code:: bash

    $ pip install gunicorn
    $ gunicorn app

Now try querying it with curl:

.. code:: bash

    $ curl localhost:8000 -v

You should get a 404. That's actually OK, because we haven't specified any
routes yet. Note that Falcon includes a default 404 response handler that
will fire for any requested path that doesn't match any routes.

Curl is a bit of a pain to use, so let's install
`HTTPie <https://github.com/jkbr/httpie>`_ and use it from now on.

.. code:: bash

    $ pip install --upgrade httpie
    $ http localhost:8000


Creating Resources
------------------

Falcon borrows some of its terminology from the REST architectural
style, so if you are familiar with that mindset, Falcon should be familiar.
On the other hand, if you have no idea what REST is, no worries; Falcon
was designed to be as intuitive as possible for anyone who understands
the basics of HTTP.

In Falcon, you map incoming requests to things called "Resources". A
Resource is just a regular Python class that includes some methods that
follow a certain naming convention. Each of these methods corresponds to
an action that the API client can request be performed in order to fetch
or transform the resource in question.

Since we are building an image-sharing API, let's create an "images"
resource. Create a new file, ``images.py`` within your project directory,
and add the following to it:

.. code:: python

    import falcon


    class Resource(object):

        def on_get(self, req, resp):
            resp.body = '{"message": "Hello world!"}'
            resp.status = falcon.HTTP_200

As you can see, ``Resource`` is just a regular class. You can name the
class anything you like. Falcon uses duck-typing, so you don't need to
inherit from any sort of special base class.

The image resource above defines a single method, ``on_get``. For any
HTTP method you want your resource to support, simply add an ``on_x``
class method to the resource, where ``x`` is any one of the standard
HTTP methods, lowercased (e.g., ``on_get``, ``on_put``, ``on_head``, etc.).

We call these well-known methods "responders". Each responder takes (at
least) two params, one representing the HTTP request, and one representing
the HTTP response to that request. By convention, these are called
``req`` and ``resp``, respectively. Route templates and hooks can inject extra
params, as we shall see later on.

Right now, the image resource responds to GET requests with a simple
``200 OK`` and a JSON body. Falcon's Internet media type defaults to
``application/json`` but you can set it to whatever you like. For example:

.. code:: python

    def on_get(self, req, resp):
        resp.data = msgpack.packb({'message': 'Hello world!''})
        resp.content_type = 'application/msgpack'
        resp.status = falcon.HTTP_200

Note the use of ``resp.data`` in lieu of ``resp.body``. If you assign a
bytestring to the latter, Falcon will figure it out, but you can
get a little performance boost by assigning directly to ``resp.data``.

OK, now let's wire up this resource and see it in action. Go back to
``app.py`` and modify it so it looks something like this:

.. code:: python

    import falcon

    import images


    api = application = falcon.API()

    images = images.Resource()
    api.add_route('/images', images)

Now, when a request comes in for "/images", Falcon will call the
responder on the images resource that corresponds to the requested
HTTP method.

Restart gunicorn, and then try sending a GET request to the resource:

.. code:: bash

    $ http GET localhost:8000/images


Request and Response Objects
----------------------------

Each responder in a resource receives a request object that can be used to
read the headers, query parameters, and body of the request. You can use
the help function mentioned earlier to list the Request class members:

.. code:: bash

    In [1]: import falcon

    In [2]: help(falcon.Request)

Each responder also receives a response object that can be used for setting
the status code, headers, and body of the response. You can list the
Response class members using the same technique used above:

.. code:: bash

    In [3]: help(falcon.Response)

Let's see how this works. When a client POSTs to our images collection, we
want to create a new image resource. First, we'll need to specify where the
images will be saved (for a real service, you would want to use an object
storage service instead, such as Cloud Files or S3).

Edit your ``images.py`` file and add the following to the resource:

.. code:: python

    def __init__(self, storage_path):
        self.storage_path = storage_path

Then, edit ``app.py`` and pass in a path to the resource initializer.

Next, let's implement the POST responder:

.. code:: python

    import os
    import time
    import uuid

    import falcon


    def _media_type_to_ext(media_type):
        # Strip off the 'image/' prefix
        return media_type[6:]


    def _generate_id():
        return str(uuid.uuid4())


    class Resource(object):

        def __init__(self, storage_path):
            self.storage_path = storage_path

        def on_post(self, req, resp):
            image_id = _generate_id()
            ext = _media_type_to_ext(req.content_type)
            filename = image_id + '.' + ext

            image_path = os.path.join(self.storage_path, filename)

            with open(image_path, 'wb') as image_file:
                while True:
                    chunk = req.stream.read(4096)
                    if not chunk:
                        break

                    image_file.write(chunk)

            resp.status = falcon.HTTP_201
            resp.location = '/images/' + image_id

As you can see, we generate a unique ID and filename for the new image, and
then write it out by reading from ``req.stream``. It's called ``stream`` instead
of ``body`` to emphasize the fact that you are really reading from an input
stream; Falcon never spools or decodes request data, instead giving you direct
access to the incoming binary stream provided by the WSGI server.

Note that we are setting the
`HTTP response status code <http://httpstatus.es>`_ to "201 Created". For a full list of
predefined status strings, simply call ``help`` on ``falcon.status_codes``:

.. code:: bash

    In [4]: help(falcon.status_codes)

The last line in the ``on_post`` responder sets the Location header for the
newly created resource. (We will create a route for that path in just a
minute.) Note that the Request and Response classes contain convenience
attributes for reading and setting common headers, but you can always
access any header by name with the ``req.get_header`` and ``resp.set_header``
methods.

Restart gunicorn, and then try sending a POST request to the resource
(substituting test.jpg for a path to any JPEG you like.)

.. code:: bash

    $ http POST localhost:8000/images Content-Type:image/jpeg < test.jpg

Now, if you check your storage directory, it should contain a copy of the
image you just POSTed.

.. _tutorial-serving-images:

Serving Images
--------------

Now that we have a way of getting images into the service, we need a way
to get them back out. What we want to do is return an image when it is
requested using the path that came back in the Location header, like so:

.. code:: bash

    $ http GET localhost:8000/images/87db45ff42

Now, we could add an ``on_get`` responder to our images resource, and that is
fine for simple resources like this, but that approach can lead to problems
when you need to respond differently to the same HTTP method (e.g., GET),
depending on whether the user wants to interact with a collection
of things, or a single thing.

With that in mind, let's create a separate class to represent a single image,
as opposed to a collection of images. We will then add an ``on_get`` responder
to the new class.

Go ahead and edit your ``images.py`` file to look something like this:

.. code:: python

    import os
    import time
    import uuid

    import falcon


    def _media_type_to_ext(media_type):
        # Strip off the 'image/' prefix
        return media_type[6:]


    def _ext_to_media_type(ext):
        return 'image/' + ext


    def _generate_id():
        return str(uuid.uuid4())


    class Collection(object):

        def __init__(self, storage_path):
            self.storage_path = storage_path

        def on_post(self, req, resp):
            image_id = _generate_id()
            ext = _media_type_to_ext(req.content_type)
            filename = image_id + '.' + ext

            image_path = os.path.join(self.storage_path, filename)

            with open(image_path, 'wb') as image_file:
                while True:
                    chunk = req.stream.read(4096)
                    if not chunk:
                        break

                    image_file.write(chunk)

            resp.status = falcon.HTTP_201
            resp.location = '/images/' + filename


    class Item(object):

        def __init__(self, storage_path):
            self.storage_path = storage_path

        def on_get(self, req, resp, name):
            ext = os.path.splitext(name)[1][1:]
            resp.content_type = _ext_to_media_type(ext)

            image_path = os.path.join(self.storage_path, name)
            resp.stream = open(image_path, 'rb')
            resp.stream_len = os.path.getsize(image_path)

As you can see, we renamed ``Resource`` to ``Collection`` and added a new ``Item``
class to represent a single image resource. Also, note the ``name`` parameter
for the ``on_get`` responder. Any URI parameters that you specify in your routes
will be turned into corresponding kwargs and passed into the target responder as
such. We'll see how to specify URI parameters in a moment.

Inside the ``on_get`` responder,
we set the Content-Type header based on the filename extension, and then
stream out the image directly from an open file handle. Note the use of
``resp.stream_len``. Whenever using ``resp.stream`` instead of ``resp.body`` or
``resp.data``, you have to also specify the expected length of the stream so
that the web client knows how much data to read from the response.

.. note:: If you do not know the size of the stream in advance, you can work around
   that by using chunked encoding, but that's beyond the scope of this
   tutorial.

If ``resp.status`` is not set explicitly, it defaults to ``200 OK``, which is
exactly what we want the ``on_get`` responder to do.

Now, let's wire things up and give this a try. Go ahead and edit ``app.py`` to
look something like this:

.. code:: python

    import falcon

    import images


    api = application = falcon.API()

    storage_path = '/usr/local/var/look'

    image_collection = images.Collection(storage_path)
    image = images.Item(storage_path)

    api.add_route('/images', image_collection)
    api.add_route('/images/{name}', image)

As you can see, we specified a new route, ``/images/{name}``. This causes
Falcon to expect all associated responders to accept a ``name``
argument.

.. note::

    Falcon currently supports Level 1
    `URI templates <https://tools.ietf.org/html/rfc6570>`_, and support for
    higher levels is planned.

Now, restart gunicorn and post another picture to the service:

.. code:: bash

    $ http POST localhost:8000/images Content-Type:image/jpeg < test.jpg

Make a note of the path returned in the Location header, and use it to
try GETing the image:

.. code:: bash

    $ http localhost:8000/images/6daa465b7b.jpeg

HTTPie won't download the image by default, but you can see that the response
headers were set correctly. Just for fun, go ahead and paste the above URI
into your web browser. The image should display correctly.


Query Strings
-------------

*Coming soon...*


Introducing Hooks
-----------------

At this point you should have a pretty good understanding of the basic parts
that make up a Falcon-based API. Before we finish up, let's just take a few
minutes to clean up the code and add some error handling.

First of all, let's check the incoming media type when something is posted
to make sure it is a common image type. We'll do this by using a Falcon
``before`` hook.

First, let's define a list of media types our service will accept. Place this
constant near the top, just after the import statements in ``images.py``:

.. code:: python

    ALLOWED_IMAGE_TYPES = (
        'image/gif',
        'image/jpeg',
        'image/png',
    )

The idea here is to only accept GIF, JPEG, and PNG images. You can add others
to the list if you like.

Next, let's create a hook that will run before each request to post a
message. Add this method below the definition of ``ALLOWED_IMAGE_TYPES``:

.. code:: python

    def validate_image_type(req, resp, params):
        if req.content_type not in ALLOWED_IMAGE_TYPES:
            msg = 'Image type not allowed. Must be PNG, JPEG, or GIF'
            raise falcon.HTTPBadRequest('Bad request', msg)

And then attach the hook to the ``on_post`` responder like so:

.. code:: python

    @falcon.before(validate_image_type)
    def on_post(self, req, resp):

Now, before every call to that responder, Falcon will first invoke the
``validate_image_type`` method. There isn't anything special about that
method, other than it must accept three arguments. Every hook takes, as its
first two arguments, a reference to the same ``req`` and ``resp`` objects
that are passed into responders. The third argument, named ``params`` by
convention, is a reference to the kwarg dictionary Falcon creates for each
request. ``params`` will contain the route's URI template params and their
values, if any.

As you can see in the example above, you can use ``req`` to get information
about the incoming request. However, you can also use ``resp`` to play with
the HTTP response as needed, and you can even inject extra kwargs for
responders in a DRY way, e.g.,:

.. code:: python

    def extract_project_id(req, resp, params):
        """Adds `project_id` to the list of params for all responders.

        Meant to be used as a `before` hook.
        """
        params['project_id'] = req.get_header('X-PROJECT-ID')

Now, you can imagine that such a hook should apply to all responders for
a resource, or even globally to all resources. You can apply hooks to an
entire resource like so:

.. code:: python

    @falcon.before(extract_project_id)
    class Message(object):

        # ...

And you can apply hooks globally by passing them into the API class
initializer:

.. code:: python

    falcon.API(before=[extract_project_id])

To learn more about hooks, take a look at the docstring for the ``API`` class,
as well the docstrings for the ``falcon.before`` and ``falcon.after`` decorators.

Now that you've added a hook to validate the media type when an image is
POSTed, you can see it in action by passing in something nefarious:

.. code:: bash

    $ http POST localhost:8000/images Content-Type:image/jpx < test.jpx

That should return a ``400 Bad Request`` status and a nicely structured
error body. When something goes wrong, you usually want to give your users
some info to help them resolve the issue. The exception to this rule is when
an error occurs because the user is requested something they are not
authorized to access. In that case, you may wish to simply return
``404 Not Found`` with an empty body, in case a malicious user is fishing
for information that will help them crack your API.

.. tip:: Please take a look at our new sister project,
   `Talons <https://github.com/talons/talons>`_, for a collection of
   useful Falcon hooks contributed by the community. Also, If you create a
   nifty hook that you think others could use, please consider
   contributing to the project yourself.

Error Handling
--------------

Generally speaking, Falcon assumes that resource responders (*on_get*,
*on_post*, etc.) will, for the most part, do the right thing. In other words,
Falcon doesn't try very hard to protect responder code from itself.

This approach reduces the number of (often) extraneous checks that Falcon
would otherwise have to perform, making the framework more efficient. With
that in mind, writing a high-quality API based on Falcon requires that:

1. Resource responders set response variables to sane values.
2. Your code is well-tested, with high code coverage.
3. Errors are anticipated, detected, and handled appropriately within each
responder.

.. tip::
    Falcon will re-raise errors that do not inherit from ``falcon.HTTPError``
    unless you have registered a custom error handler for that type
    (see also: :ref:`falcon.API <api>`).

Speaking of error handling, when something goes horribly (or mildly) wrong,
you *could* manually set the error status, appropriate response headers, and
even an error body using the ``resp`` object. However, Falcon tries to make
things a bit easier by providing a set of exceptions you can raise when
something goes wrong. In fact, if Falcon catches any exception your responder
throws that inherits from ``falcon.HTTPError``, the framework will convert
that exception to an appropriate HTTP error response.

You may raise an instance of ``falcon.HTTPError``, or use any one
of a number of predefined error classes that try to do "the right thing" in
setting appropriate headers and bodies. Have a look at the docs for
any of the following to get more information on how you can use them in your
API:

.. code:: python

    falcon.HTTPBadGateway
    falcon.HTTPBadRequest
    falcon.HTTPConflict
    falcon.HTTPError
    falcon.HTTPForbidden
    falcon.HTTPInternalServerError
    falcon.HTTPLengthRequired
    falcon.HTTPMethodNotAllowed
    falcon.HTTPNotAcceptable
    falcon.HTTPNotFound
    falcon.HTTPPreconditionFailed
    falcon.HTTPRangeNotSatisfiable
    falcon.HTTPServiceUnavailable
    falcon.HTTPUnauthorized
    falcon.HTTPUnsupportedMediaType
    falcon.HTTPUpgradeRequired

For example, you could handle a missing image file like this:

.. code:: python

    try:
        resp.stream = open(image_path, 'rb')
    except IOError:
        raise falcon.HTTPNotFound()

Or you could handle a bogus filename like this:

.. code:: python

    VALID_IMAGE_NAME = re.compile(r'[a-f0-9]{10}\.(jpeg|gif|png)$')

    # ...

    class Item(object):

        def __init__(self, storage_path):
            self.storage_path = storage_path

        def on_get(self, req, resp, name):
            if not VALID_IMAGE_NAME.match(name):
                raise falcon.HTTPNotFound()

Sometimes you don't have much control over the type of exceptions that get
raised. To address this, Falcon lets you create custom handlers for any type
of error. For example, if your database throws exceptions that inherit from
NiftyDBError, you can install a special error handler just for NiftyDBError,
so you don't have to copy-paste your handler code across multiple responders.

Have a look at the docstring for ``falcon.API.add_error_handler`` for more
information on using this feature to DRY up your code:

.. code:: python

    In [71]: help(falcon.API.add_error_handler)

What Now?
---------

Our friendly community is available to answer your questions and help you
work through sticky problems. See also: :ref:`Getting Help <help>`.

As mentioned previously, Falcon's docstrings are quite extensive, and so you
can learn a lot just by poking around Falcon's modules from a Python REPL,
such as `IPython <http://ipython.org/>`_ or
`bpython <http://bpython-interpreter.org/>`_.

Also, don't be shy about pulling up Falcon's source code on GitHub or in your
favorite text editor. The team has tried to make the code as straightforward
and readable as possible; where other documentation may fall short, the code basically
"can't be wrong."


