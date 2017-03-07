.. _tutorial:

Tutorial
========

In this tutorial we'll walk through building an API for a simple image sharing
service. Along the way, we'll discuss Falcon's major features and introduce
the terminology used by the framework.

First Steps
-----------

Before continuing, be sure you've got Falcon :ref:`installed <install>` inside
a `virtualenv <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_.
Then, create a new project folder called "look" and cd into it:

.. code:: bash

    $ mkdir look
    $ cd look

It's customary for the project's top-level module to be called the same as the
project, so let's create another "look" folder inside the first one and mark
it as a python module by creating an empty ``__init__.py`` file in it:

.. code:: bash

    $ mkdir look
    $ touch look/__init__.py

Next, let's create a new file that will be the entry point into your app:

.. code:: bash

    $ touch look/app.py

The file hierarchy should look like this:

.. code:: bash

    look
    └── look
        ├── app.py
        └── __init__.py

Now, open ``app.py`` in your favorite text editor and add the following lines:

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

    `bpython <http://bpython-interpreter.org/>`_ or
    `ptpython <https://github.com/jonathanslenders/ptpython>`_ are other
    super-powered REPLs that are good to have in your toolbox when exploring
    a new library.


Hosting Your App
----------------

Now that you have a simple Falcon app, you can take it for a spin with
a WSGI server. Python includes a reference server for self-hosting, but
let's use something that you would actually deploy in production.

.. code:: bash

    $ pip install gunicorn
    $ gunicorn look.app

If you are a Windows user, then use Waitress instead of Gunicorn, since the latter
doesn't work under Windows.

.. code:: bash

    $ pip install waitress
    $ waitress-serve --port=8000 look.app

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
resource. Create a new file, ``images.py`` next to ``app.py``, and add the
following to it:

.. code:: python

    import falcon


    class Resource(object):

        def on_get(self, req, resp):
            resp.body = '{"message": "Hello world!"}'
            # This line can be ommited, because 200 is the default code falcon
            # returns, but it shows how you can set a status code.
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
``application/json`` but you can set it to whatever you like. For example,
you could use `MessagePack <http://msgpack.org/>`_, or any other
serialization format.

If you'd like to use MessagePack in the above example, you'll need to
install the (de)serializer for Python running ``pip install msgpack-python``
and then update your responder to set the response data and content_type
accordingly:

.. code:: python

    import falcon

    import msgpack


    class Resource(object):

        def on_get(self, req, resp):
            resp.data = msgpack.packb({'message': 'Hello world!'})
            resp.content_type = 'application/msgpack'
            resp.status = falcon.HTTP_200

Note the use of ``resp.data`` in lieu of ``resp.body``. If you assign a
bytestring to the latter, Falcon will figure it out, but you can
get a little performance boost by assigning directly to ``resp.data``.

OK, now let's wire up this resource and see it in action. Go back to
``app.py`` and modify it so it looks something like this:

.. code:: python

    import falcon

    from .images import Resource


    api = application = falcon.API()

    images = Resource()
    api.add_route('/images', images)

Now, when a request comes in for "/images", Falcon will call the
responder on the images resource that corresponds to the requested
HTTP method.

Restart Gunicorn, and then try sending a GET request to the resource:

.. code:: bash

    $ http GET localhost:8000/images

Testing your application
------------------------

Up to this point we didn't care about tests, but fully exercising your code is critical
to creating robust applications with a great user experience.
So, to practise that, we'll create
the next piece of code in accordance with Test Driven Development (TDD).

.. note:: There's a good book on TDD called
   `Test Driven Development with Python
   <http://www.obeythetestinggoat.com/book/praise.harry.html>`_.
   The examples in the book use the Django framework and even JavaScript, but the presented
   testing principles can be applied to all web development.

But let's first write the missing tests for the current behavior of the application.
Create a ``tests`` directory with ``__init__.py`` and the test file (``test_app.py``)
inside it. The project's structure should look like this:

.. code:: bash

    look
    ├── look
    │   ├── app.py
    │   ├── images.py
    │   └── __init__.py
    └── tests
        ├── __init__.py
        └── test_app.py

Falcon supports unit testing its API object by simulating HTTP requests.
There are two styles of writing tests - using built-in unittest module, and with pytest
(more details can be found in :ref:`testing reference <testing>`). pytest may not
be a part of Python's standard library, but it allows for more "pythonic" test code
than unittest which is highly influenced by Java's JUnit;
therefore, we'll stick with pytest. Let's install it

.. code:: bash

    $ pip install pytest

and edit ``test_app.py`` to look like this:

.. code:: python

    import falcon
    from falcon import testing
    import msgpack
    import pytest

    from look.app import api


    @pytest.fixture
    def client():
        return testing.TestClient(api)


    # pytest will inject the object returned by the "client" function as a parameter
    # for this function.
    def test_get_message(client):
        doc = {u'message': u'Hello world!'}

        response = client.simulate_get('/images')
        result_doc = msgpack.unpackb(response.content, encoding='utf-8')

        assert result_doc == doc
        assert response.status == falcon.HTTP_OK

See your tests pass by running pytest against the ``tests`` directory while in the main
project directory.

.. code:: bash

    py.test tests/

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

This will be useful when creating a POST endpoint in the application that can
add new image resources to our collection. Because we decided to do TDD, we need
to create a test for this feature **before** we write the code for it.
That way we define precisely what we want the application to do, and then code until
the tests tell us that we're done.
To that end, let's add some imports in ``test_app.py``:

.. code:: python

    from unittest.mock import mock_open, call

...and then add a new test:

.. code:: python

    # "monkeypatch" is a special built-it fixture that can be used to mock out various things.
    def test_posted_image_gets_saved(client, monkeypatch):
        mock_file_open = mock_open()
        fake_uuid = 'blablabla'
        fake_image_bytes = b'fake-image-bytes'
        monkeypatch.setattr('builtins.open', mock_file_open)
        monkeypatch.setattr('look.images.uuid.uuid4', lambda: fake_uuid)

        # When the service receives an image through POST...
        response = client.simulate_post('/images',
                                        body=fake_image_bytes,
                                        headers={'content-type': 'image/png'})

        # ...it must return a 201 code, save the file, and return the image's resource location.
        assert response.status == falcon.HTTP_CREATED
        assert call().write(fake_image_bytes) in mock_file_open.mock_calls
        assert response.headers['location'] == '/images/{}.png'.format(fake_uuid)

As you can see, this test relies heavily on mocking, thus making
it fragile in the face of implementation changes. We'll deal with this later.
But for now, run the tests again to see that they fail.
Making sure that your tests **don't** pass when they shouldn't is an integral part of TDD.

Now, we can finally get to the resource implementation. We'll need to add a new method for
handling POSTs, and specify where the images will be saved (for a real service, you would
want to use an object storage service instead, such as Cloud Files or S3).

Next, let's implement the POST responder in ``images.py``:

.. code:: python

    import os
    import uuid
    import mimetypes

    import falcon
    import msgpack


    class Resource(object):

        # the resource object must now be initialized with a path used during POST
        def __init__(self, storage_path):
            self.storage_path = storage_path

        # this is the method we implemented before
        def on_get(self, req, resp):
            resp.data = msgpack.packb({'message': 'Hello world!'})
            resp.content_type = 'application/msgpack'
            resp.status = falcon.HTTP_200

        def on_post(self, req, resp):
            ext = mimetypes.guess_extension(req.content_type)
            filename = '{uuid}{ext}'.format(uuid=uuid.uuid4(), ext=ext)
            image_path = os.path.join(self.storage_path, filename)

            with open(image_path, 'wb') as image_file:
                while True:
                    chunk = req.stream.read(4096)
                    if not chunk:
                        break

                    image_file.write(chunk)

            resp.status = falcon.HTTP_201
            resp.location = '/images/' + filename

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

With that explained, we can move onto making our service work.
Edit ``app.py`` and pass in a path to the resource initializer.
For now, it can be the working directory from which you started the service.

.. code:: python

    images = Resource(storage_path='.')

Now you can run the tests again and see them pass!

You can also restart Gunicorn, and then try sending a POST request to the resource
yourself (substituting ``test.png`` for a path to any PNG you like.)

.. code:: bash

    $ http POST localhost:8000/images Content-Type:image/png < test.png

Now, if you check your storage directory, it should contain a copy of the
image you just POSTed.


Refactoring for testability
---------------------------

As you remember, our POST test had a lot of mocks and could break easily if
the underlying implementation changed. To remedy this situation, we not only
need to refactor the tests, but also the code, to facilitate easier testing.

First, let's separate the "business logic" from the POST resource's
code in ``images.py`` by factoring out the saving of a file.

.. code:: python

    import mimetypes
    import os
    import uuid

    import falcon
    import msgpack


    class Resource(object):

        def __init__(self, image_saver):
            self.image_saver = image_saver

        def on_get(self, req, resp):
            resp.data = msgpack.packb({'message': 'Hello world!'})
            resp.content_type = 'application/msgpack'
            resp.status = falcon.HTTP_200

        def on_post(self, req, resp):
            filename = self.image_saver.save(req.stream, req.content_type)
            resp.status = falcon.HTTP_201
            resp.location = '/images/' + filename


    class ImageSaver:

        def __init__(self, storage_path):
            self.storage_path = storage_path

        def save(self, image_stream, image_content_type):
            ext = mimetypes.guess_extension(image_content_type)
            filename = '{uuid}{ext}'.format(uuid=uuid.uuid4(), ext=ext)
            image_path = os.path.join(self.storage_path, filename)

            with open(image_path, 'wb') as image_file:
                while True:
                    chunk = image_stream.read(4096)
                    if not chunk:
                        break

                    image_file.write(chunk)
            return filename

By our careless meddling, we, of course, broke the application, and running the tests
assures us of that. But the power of tests lie in that they will show us when the
application works again and the refactor is complete.
You can run them after every code change from now on to observe when that happens.

Let's adjust ``app.py``:

.. code:: python

    import falcon

    from .images import ImageSaver, Resource


    def create_app(image_saver):
        image_resource = Resource(image_saver)
        api = falcon.API()
        api.add_route('/images', image_resource)
        return api


    def get_app():
        image_saver = ImageSaver('.')
        return create_app(image_saver)

``create_app`` can be used to obtain a unit-testable or production API object.
``get_app`` holds the service's "production" (real running) configuration.
You can configure logging there, set up production resources, etc.
Most of the time a function like this will get in the way of unit testing,
so we can keep it here to be used when the app is run by Gunicorn.
The command to run the application is now:

.. code:: bash

    $ gunicorn 'look.app:get_app()'

On to the tests that we wanted to redo in the first place:

.. code:: python

    import io
    from unittest.mock import call, MagicMock, mock_open

    import falcon
    from falcon import testing
    import msgpack
    import pytest

    import look.app
    import look.images


    @pytest.fixture
    def mock_saver():
        return MagicMock()


    @pytest.fixture
    def client(mock_saver):
        api = look.app.create_app(mock_saver)
        return testing.TestClient(api)


    def test_get_message(client):
        doc = {u'message': u'Hello world!'}

        response = client.simulate_get('/images')
        result_doc = msgpack.unpackb(response.content, encoding='utf-8')

        assert result_doc == doc
        assert response.status == falcon.HTTP_OK


    # With clever composition of fixtures, we can observe what happens with
    # the mock injected into the image resource.
    def test_post_image(client, mock_saver):
        file_name = 'fake-image-name.xyz'
        # we need to know what ImageSaver method will be used
        mock_saver.save.return_value = file_name
        image_content_type = 'image/xyz'

        response = client.simulate_post('/images',
                                        body=b'some-fake-bytes',
                                        headers={'content-type': image_content_type})

        assert response.status == falcon.HTTP_CREATED
        assert response.headers['location'] == '/images/{}'.format(file_name)
        saver_call = mock_saver.save.call_args
        # saver_call is a unittest.mock.call tuple.
        # It's first element is a tuple of positional arguments supplied when calling the mock.
        assert isinstance(saver_call[0][0], falcon.request_helpers.BoundedStream)
        assert saver_call[0][1] == image_content_type

As you can see, we've redone the POST. While there are fewer mocks, the assertions
have gotten more elaborate to properly check the interactions on interface boundaries;
we're also not covering the actual saving now (test coverage reports are useful to
detect this kind of situations), so let's add that.

.. code:: python

    def test_saving_image(monkeypatch):
        mock_file_open = mock_open()
        monkeypatch.setattr('builtins.open', mock_file_open)
        fake_uuid = 'blablabla'
        monkeypatch.setattr('look.images.uuid.uuid4', lambda: fake_uuid)

        fake_image_bytes = b'fake-image-bytes'
        fake_request_stream = io.BytesIO(fake_image_bytes)
        storage_path = 'fake-storage-path'
        saver = look.images.ImageSaver(storage_path)

        assert saver.save(fake_request_stream, 'image/png') == fake_uuid + '.png'
        assert call().write(fake_image_bytes) in mock_file_open.mock_calls

Like the former test, this one is also still plagued by mocks and the ensuing brittleness.
But the logical structure of the code is better, so the resource and image saving
(and their tests) can be develop independently in the future, reducing the impact
of tying tests to implementation.

It's also worth noting that the purpose of this whole refactor is to demonstrate a useful
technique for real-life projects, rather than simply making our minimal application's
tests better.

Also, it seems that we didn't actually obey TDD by changing the code first and the tests later.
But it would be really hard to write the tests without first knowing the implementation,
as well as how the mocks should be defined and injected, right? Of course!
That's why real TDD usually employs a second layer of tests, called functional (or integration,
or other names; it's a nuanced thing worth looking into on your own) tests.
They exercise the application as a whole, not bothering with mocking, the same way its
normal user (which can be a different program or a human) would.


Functional tests
----------------

Functional tests define the application's behavior from the outside. They are much
easier to write before the code than unit tests that will require mocking (not all
of them do, though). In the case of the refactoring work from the last section, we could have
inadvertently introduced a bug into the application that might have been masked when we rewrote
the tests to make them pass. Functional tests would prevent us from doing that. They should
actually be written before any unit tests or application code, but we wanted to get into Falcon
testing before going over good TDD practices.

In our case (and in the case of most web applications) the idea behind a functional test
is to run the application as a normal, separate process (e.g. with Gunicorn) and
then to interract with it as a normal client would - through HTTP calls. Before we
implement that, it would be useful to add the ability to configure the image
storage directory through an environment variable in ``app.py``.

.. code:: python

    def get_app():
        storage_path = os.environ.get('LOOK_STORAGE', '.')
        image_saver = ImageSaver(storage_path)
        return create_app(image_saver)

To run the app with a non-default storage directory, just do:

.. code:: bash

    $ LOOK_STORAGE=/tmp gunicorn 'look.app:get_app()'

Now, put this functional test in a new test file (e.g. ``tests/test_functional.py``):

.. code:: python

    import requests


    def test_posted_image_gets_saved():
        location_prefix = '/images/'
        fake_image_bytes = b'fake-image-bytes'

        response = requests.post('http://localhost:8000/images',
                      data=fake_image_bytes,
                      headers={'content-type': 'image/png'})

        assert response.status_code == 201
        location = response.headers['location']
        assert location.startswith(location_prefix)
        filename = location.replace(location_prefix, '')
        # assuming that the storage path is "/tmp"
        with open('/tmp/' + filename, 'rb') as image_file:
            assert image_file.read() == fake_image_bytes

Running this test isn't ideal. You need to manually start the service beforehand
(with the proper hardcoded storage path), stop the service and clean up the image
files afterwards. Of course, you could automate the process of starting, stopping,
and cleaning up after the application. And put that automation into the test code
itself, hopefully in some fixtures. Libraries such as `mountepy <https://github.com/butla/mountepy>`_
can help with these tasks.

Anyway, with the new integration test in place we can remove the assertions that check
the parameters with which ``ImageSaver.save`` was called by the POST resource. Well, actually,
we could remove both ``test_post_image`` and ``test_saving_image``, because
they don't check anything more than ``test_posted_image_gets_saved``. But we can
do that only because our application's logic is rather simple.

Normally, you would check component integration and all primary logic paths
throughout the entire application with functional tests, and leave the bulk of testing
to unit tests. But the actual ratio of unit/functional tests depends entirely
on each application's problem domain, and will vary.

After this section we'll omit the TDD instructions, as you should have a good grip
of testing Falcon applications by now. Instead, we'll focus on showcasing some more of the
framework's features.

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
    import uuid
    import mimetypes

    import falcon


    class Collection(object):

        def __init__(self, storage_path):
            self.storage_path = storage_path

        def on_post(self, req, resp):
            ext = mimetypes.guess_extension(req.content_type)
            filename = '{uuid}{ext}'.format(uuid=uuid.uuid4(), ext=ext)
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
            resp.content_type = mimetypes.guess_type(name)[0]
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

    Falcon also supports more complex parameterized path segments containing
    multiple values. For example, a GH-like API could use the following
    template to add a route for diffing two branches::

        /repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}

Now, restart Gunicorn and post another picture to the service:

.. code:: bash

    $ http POST localhost:8000/images Content-Type:image/png < test.png

Make a note of the path returned in the Location header, and use it to
try GETing the image:

.. code:: bash

    $ http localhost:8000/images/6daa465b7b.png

HTTPie won't download the image by default, but you can see that the response
headers were set correctly. Just for fun, go ahead and paste the above URI
into your web browser. The image should display correctly.


.. Query Strings
.. -------------

.. *Coming soon...*

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

    def validate_image_type(req, resp, resource, params):
        if req.content_type not in ALLOWED_IMAGE_TYPES:
            msg = 'Image type not allowed. Must be PNG, JPEG, or GIF'
            raise falcon.HTTPBadRequest('Bad request', msg)

And then attach the hook to the ``on_post`` responder like so:

.. code:: python

    @falcon.before(validate_image_type)
    def on_post(self, req, resp):

Now, before every call to that responder, Falcon will first invoke the
``validate_image_type`` method. There isn't anything special about that
method, other than it must accept four arguments. Every hook takes, as its
first two arguments, a reference to the same ``req`` and ``resp`` objects
that are passed into responders. ``resource`` argument is a Resource instance
associated with the request. The fourth argument, named ``params`` by
convention, is a reference to the kwarg dictionary Falcon creates for each
request. ``params`` will contain the route's URI template params and their
values, if any.

As you can see in the example above, you can use ``req`` to get information
about the incoming request. However, you can also use ``resp`` to play with
the HTTP response as needed, and you can even inject extra kwargs for
responders in a DRY way, e.g.,:

.. code:: python

    def extract_project_id(req, resp, resource, params):
        """Adds `project_id` to the list of params for all responders.

        Meant to be used as a `before` hook.
        """
        params['project_id'] = req.get_header('X-PROJECT-ID')

Now, you can imagine that such a hook should apply to all responders for
a resource. You can apply hooks to an entire resource like so:

.. code:: python

    @falcon.before(extract_project_id)
    class Message(object):

        # ...

Similar logic can be applied globally with middleware.
(See :ref:`falcon.middleware <middleware>`)

To learn more about hooks, take a look at the docstring for the ``API`` class,
as well the docstrings for the ``falcon.before`` and ``falcon.after`` decorators.

Now that you've added a hook to validate the media type when an image is
POSTed, you can see it in action by passing in something nefarious:

.. code:: bash

    $ http POST localhost:8000/images Content-Type:image/jpx @test.jpx

That should return a ``400 Bad Request`` status and a nicely structured
error body. When something goes wrong, you usually want to give your users
some info to help them resolve the issue. The exception to this rule is when
an error occurs because the user is requested something they are not
authorized to access. In that case, you may wish to simply return
``404 Not Found`` with an empty body, in case a malicious user is fishing
for information that will help them crack your API.

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
and readable as possible; where other documentation may fall short, the code
basically "can't be wrong."

A number of Falcon add-ons, templates, and complimentary packages are
available for use in your projects. We've listed several of these on the
`Falcon wiki <https://github.com/falconry/falcon/wiki>`_ as a starting
point, but you may also wish to search PyPI for additional resources.
