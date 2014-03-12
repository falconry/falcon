.. _tutorial:

Tutorial
========

This page walks you through building an API for an image-sharing service. Along
the way, you will learn about Falcon's features and the terminology used by
the framework. You'll also learn how to query Falcon's docstrings, and get a
quick overview of the WSGI standard.

.. introduce talons, etc.
.. also create a separate FAQ

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

..code:: python

    import falcon

    api = application = falcon.API()

That creates your WSGI application and aliases it as `api`. You can use any
variable names you like, but we'll use `application` since that is what
Gunicorn expects it to be called, by default.

A WSGI application is just a callable with a well-defined signature so that
you can host the application with any web server that understands the
protocol. Let's take a look at the falcon.API class.

First, install IPython (if you don't already have it), and fire it up:

..code:: bash

    $ pip install ipython
    $ ipython

Now, type the following to introspect the falcon.API callable:

..code:: bash

    In [1]: import falcon

    In [2]: falcon.API.__call__?

Alternatively, you can use the built-in `help` function:

..code:: bash

    In [3]: help(falcon.API.__call__)

Note the method signature. `env` and `start_response` are standard
WSGI params. Falcon adds a thin abstraction on top of these params
so you don't have to interact with them directly.

The Falcon framework contains extensive inline documentation that you can
query using the above technique. The docstrings have been optimized for
human-readability, and contain no silly markup to get in your way.


Hosting Your App
----------------

Now that you have a simple Falcon app, you can take it for a spin with
a WSGI server. Python includes a reference server for self-hosting, but
let's use something that you would actually deploy in production.

..code:: bash

    $ pip install gunicorn
    $ gunicorn app

Now try querying it with curl:

..code:: bash

    $ curl localhost:8000 -v

You should get a 404. That's actually OK, because we haven't specified any
routes yet. Note that Falcon includes a default 404 response handler that
will fire for any requested path that doesn't match any routes.

Curl is a bit of a pain to use, so let's install
`HTTPie <https://github.com/jkbr/httpie>`_ and use it from now on.

..code:: bash

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
resource. Create a new file, `images.py` within your project directory,
and add the following to it:

..code:: python

    import falcon


    class Resource(object):

        def on_get(self, req, resp):
            resp.body = '{"message": "Hello world!"}'
            resp.status = falcon.HTTP_200

As you can see, `Resource` is just a regular class. You can name the
class anything you like. Falcon uses duck-typing, so you don't need to
inherit from any sort of special base class.

The image resource above defines a single method, `on_get`. For any
HTTP method you want your resource to support, simply add an `on_x`
class method to the resource, where `x` is any one of the standard
HTTP methods, lowercased (e.g., `on_get`, `on_put`, `on_head`, etc.).

We call these well-known methods "responders". Each responder takes (at
least) two params, one representing the HTTP request, and one representing
the HTTP response to that request. By convention, these are called
`req` and `resp`, respectively. Route templates and hooks can inject extra
params, as we shall see later on.

Right now, the image resource responds to GET requests with a simple
`200 OK` and a JSON body. Falcon's Internet media type defaults to
`application/json` but you can set it to whatever you like. For example:

..code:: python

    def on_get(self, req, resp):
        resp.data = msgpack.packb({'message': 'Hello world!''})
        resp.content_type = 'application/msgpack'
        resp.status = falcon.HTTP_200

Note the use of `resp.data` in lieu of `resp.body`. If you assign a
bytestring to the latter, Falcon will figure it out, but you can
get a little performance boost by assigning directly to `resp.data`.

OK, so now let's wire up this resource and see it in action. Go back to
`app.py` and modify it so it looks something like this:

..code:: python

    import falcon

    import images


    api = application = falcon.API()

    images = images.Resource()
    api.add_route('/images', images)

Now, when a request comes in for "/images", Falcon will call the
responder on the images resource that corresponds to the requested
HTTP method.

Restart gunicorn, and then try sending a GET request to the resource:

..code:: bash

    $ http GET localhost:8000/images


Request and Response Objects
----------------------------

Each responder in a resource receives a request object that can be used to
read the headers, query parameters, and body of the request. You can use
the help function mentioned earlier to list the Request class members:

..code:: bash

    In [1]: import falcon

    In [2]: help(falcon.Request)

Each responder also receives a response object that can be used for setting
the status code, headers, and body of the response. You can list the
Response class members using the same technique used above:

..code:: bash

    In [3]: help(falcon.Response)

Let's see how this works. When a client POSTs to our images collection, we
want to create a new image resource. First, we'll need to specify where the
images will be saved (for a real service, you would want to use an object
storage service instead, such as Cloud Files or S3).

Edit your `images.py` file and add the following to the resource:

..code:: python

    def __init__(self, storage_path):
        self.storage_path = storage_path

Next, edit `app.py` and pass in a path to the resource initializer. For now,
it's just fine to hard-code the string.

..code:: python

Now, let's implement the POST responder:

..code:: python

    import os
    import time

    import falcon


    def _media_type_to_ext(media_type):
        # Strip off the 'image/' prefix
        return media_type[6:]


    def _generate_id():
        return os.urandom(2).encode('hex') + hex(int(time.time() * 10))[5:]


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
then write it out by reading from `req.stream`. It's called `stream` instead
of `body` to emphasize the fact that you are really reading from an input
stream; Falcon never spools or decodes request data, instead giving you direct
access to the incoming binary stream provided by the WSGI server.

Note that we are setting the status to '201 Created'. For a full list of
predefined status strings, simply call `help` on `falcon.status_codes`:

..code:: bash

    In [4]: help(falcon.status_codes)

The last line in the `on_post` responder sets the Location header for the
newly created resource. (We will create a route for that path in just a
minute.) Note that the Request and Response classes contain convenience
attributes for reading and setting common headers, but you can always
access any header by name with the `req.get_header` and `resp.set_header`
methods.

Restart gunicorn, and then try sending a POST request to the resource
(substituting test.jpg for a path to any JPEG you like.)

..code:: bash

    $ http POST localhost:8000/images Content-Type:image/jpeg < test.jpg

Now, if you check your storage directory, it should contain a copy of the
image you just POSTed.


Serving Images
--------------

Now that we have a way of getting images into the service, we need a way
to get them back out! What we want to do is return an image when it is
requested using the path that we returned in the Location header when that
image was originally POSTed. Something like this:

..code:: bash

    $ http GET localhost:8000/images/87db45ff42

Now, we could add an `on_get` responder to our images resource, and that is
fine for simple resources like this, but that approach can lead to problems
when you need to respond differently to the same HTTP method (e.g., GET,
POST, etc.) depending on whether the user wants to interact with a collection
of things, or a single thing.

With that in mind, let's create a separate class to represent a single image,
as opposed to a collection of images. We will then add an `on_get` responder
to the new class.

Edit your `images.py` file to look something like this:

..code:: python

    import os
    import time

    import falcon


    def _media_type_to_ext(media_type):
        # Strip off the 'image/' prefix
        return media_type[6:]


    def _ext_to_media_type(ext):
        return 'image/' + ext


    def _generate_id():
        return os.urandom(2).encode('hex') + hex(int(time.time() * 10))[5:]


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

As you can see, we renamed `Resource` to `Collection` and added a new `Item`
class to represent a single image resource. Inside the `on_get` responder,
we set the Content-Type header based on the filename extension, and then
stream out the image directly from an open file handle. Note the use of
`resp.stream_len`. Whenever using `resp.stream` instead of `resp.body` or
`resp.data`, you have to also specify the expected length of the stream so
that the web client knows how much data to read from the response.

..note::

    If you do not know the size of the stream in advance, you can work around
    that by using chunked encoding, but that is beyond the scope of this
    tutorial.

If `resp.status` is not set explicitly, it defaults to `200 OK`, which is
exactly what we want for the `on_get` responder.

Now, let's see this in action. First, we need to edit `app.py` to wire up the
new resource:

..code:: python

    import falcon

    import images


    api = application = falcon.API()

    storage_path = '/usr/local/var/look'

    image_collection = images.Collection(storage_path)
    image = images.Item(storage_path)

    api.add_route('/images', image_collection)
    api.add_route('/images/{name}', image)

Now, restart gunicorn and post another picture to the service:

..code:: bash

    $ http POST localhost:8000/images Content-Type:image/jpeg < test.jpg

Make a note of the path returned in the Location header, and use it to
try GETing the image:

..code:: bash

    $ http localhost:8000/images/6daa465b7b.jpeg

HTTPie won't download the image by default, but you can see that the response
headers were set correctly. Just for fun, go ahead and paste the above URI
into your web browser. The image should display correctly.


Finishing Touches
-----------------

*Coming soon*

.. resp.stream - using wsgi.file_wrapper
.. verify content-type on message post (DRY with hooks, show before and after)
.. handle image name not found in the "get"
.. validate image name format
.. ensure client accepts the image type that will be returned
.. mention Talons
..

.. talk about list vs. single, DRY things with hooks (show before and after) and mention Talons

What Now?
---------

*Coming soon*