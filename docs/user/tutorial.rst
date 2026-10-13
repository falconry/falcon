.. _tutorial:

Tutorial (WSGI)
===============

In this tutorial we'll walk through building an API for a simple image sharing
service. Along the way, we'll discuss Falcon's major features and introduce
the terminology used by the framework.

.. note::
   This tutorial covers the "traditional", synchronous flavor of Falcon using
   the `WSGI <https://www.python.org/dev/peps/pep-3333/>`__ protocol.

   Developing an ``async`` application? Check out our
   :ref:`ASGI tutorial<tutorial-asgi>` instead!

.. _tutorial-first-steps:

First Steps
-----------

The first thing we'll do is :ref:`install <install>` Falcon
inside a fresh
`virtualenv <https://docs.python-guide.org/en/latest/dev/virtualenvs/>`_.
To that end, let's create a new project folder called "look", and set
up a virtual environment within it that we can use for the tutorial:

.. code:: bash

    $ mkdir look
    $ cd look
    $ virtualenv .venv
    $ source .venv/bin/activate
    $ pip install falcon

It's customary for the project's top-level module to be called the same as the
project, so let's create another "look" folder inside the first one and mark
it as a python module by creating an empty ``__init__.py`` file in it:

.. code:: bash

    $ mkdir look
    $ touch look/__init__.py

Next, let's create a new file that will be the entry point into your app:

.. code:: bash

    $ touch look/app.py

The file hierarchy should now look like this:

.. code:: bash

    look
    ├── .venv
    └── look
        ├── __init__.py
        └── app.py

Now, open ``app.py`` in your favorite text editor and add the following lines:

.. literalinclude:: ../../examples/look/versions/01_app.py
    :language: python

This code creates your WSGI application and aliases it as ``app``. You can use any
variable names you like, but we'll use ``application`` since that is what
Gunicorn, by default, expects it to be called (we'll see how this works
in the next section of the tutorial).

.. note::
    A WSGI application is just a callable with a well-defined signature so that
    you can host the application with any web server that understands the `WSGI
    protocol <https://peps.python.org/pep-3333/>`_.

Next let's take a look at the :class:`falcon.App` class. Install
`IPython <https://ipython.org/>`_ and fire it up:

.. code:: bash

    $ pip install ipython
    $ ipython

Now, type the following to introspect the :class:`falcon.App` callable:

.. code:: bash

    In [1]: import falcon

    In [2]: falcon.App.__call__?

Alternatively, you can use the standard Python ``help()`` function:

.. code:: bash

    In [3]: help(falcon.App.__call__)

Note the method signature. ``env`` and ``start_response`` are standard
WSGI params. Falcon adds a thin abstraction on top of these params
so you don't have to interact with them directly.

The Falcon framework contains extensive inline documentation that you
can query using the above technique.

.. tip::

    In addition to `IPython <https://ipython.org/>`_, the Python
    community maintains several other super-powered REPLs
    that you may wish to try, including
    `bpython <https://bpython-interpreter.org/>`_
    and
    `ptpython <https://github.com/jonathanslenders/ptpython>`_.

Hosting Your App
----------------

Now that you have a simple Falcon app, you can take it for a spin with
a WSGI server. Python includes a reference server for self-hosting, but
let's use something more robust that you might use in production.

Open a new terminal and run the following:

.. code:: bash

    $ source .venv/bin/activate
    $ pip install gunicorn
    $ gunicorn --reload look.app

(Note the use of the ``--reload`` option to tell Gunicorn to reload the
app whenever its code changes.)

If you are a Windows user, Waitress can be used in lieu of Gunicorn,
since the latter doesn't work under Windows:

.. code:: bash

    $ pip install waitress
    $ waitress-serve --port=8000 look.app:app

Now, in a different terminal, try querying the running app with curl:

.. code:: bash

    $ curl -v localhost:8000

You should get a 404. That's actually OK, because we haven't specified
any routes yet. Falcon includes a default 404 response handler that
will fire for any requested path for which a route does not exist.

While curl certainly gets the job done, it can be a bit crufty to use.
`HTTPie <https://github.com/jkbr/httpie>`_ is a modern,
user-friendly alternative. Let's install HTTPie and use it from now on:

.. code:: bash

    $ source .venv/bin/activate
    $ pip install httpie
    $ http localhost:8000


.. _tutorial_resources:

Creating Resources
------------------

Falcon's design borrows several key concepts from the REST architectural
style.

Central to both REST and the Falcon framework is the concept of a
"resource". Resources are simply all the things in your API or
application that can be accessed by a URL. For example, an event booking
application may have resources such as "ticket" and "venue", while a
video game backend may have resources such as "achievements" and
"player".

URLs provide a way for the client to uniquely identify resources. For
example, ``/players`` might identify the "list of all players" resource,
while ``/players/45301f54`` might identify the "individual player with
ID 45301f54", and ``/players/45301f54/achievements`` the
"list of all achievements for the player resource with ID 45301f54".

.. code::

      POST        /players/45301f54/achievements
    └──────┘    └────────────────────────────────┘
     Action            Resource Identifier

In the REST architectural style, the URL only
identifies the resource; it does not specify what action to take on
that resource. Instead, users choose from a set of standard methods.
For HTTP, these are the familiar GET, POST, HEAD, etc. Clients can
query a resource to discover which methods it supports.

.. note::

    This is one of the key differences between the REST and RPC
    architectural styles. REST applies a standard set of
    verbs across any number of resources, as opposed to
    having each application define its own unique set of methods.

Depending on the requested action, the server may or may not return a
representation to the client. Representations may be encoded in
any one of a number of Internet media types, such as JSON and HTML.

Falcon uses Python classes to represent resources. In practice, these
classes act as controllers in your application. They convert an
incoming request into one or more internal actions, and then compose a
response back to the client based on the results of those actions.

.. code::

               ┌────────────┐
    request  → │            │
               │ Resource   │ ↻ Orchestrate the requested action
               │ Controller │ ↻ Compose the result
    response ← │            │
               └────────────┘

A resource in Falcon is just a regular Python class that includes
one or more methods representing the standard HTTP verbs supported by
that resource. Each requested URL is mapped to a specific resource.

Since we are building an image-sharing API, let's start by creating an
"images" resource. Create a new module, ``images.py`` next to ``app.py``,
and add the following code to it:

.. literalinclude:: ../../examples/look/versions/02_images.py
    :language: python

As you can see, ``Resource`` is just a regular class. You can name the
class anything you like. Falcon uses duck-typing, so you don't need to
inherit from any sort of special base class.

The image resource above defines a single method, ``on_get()``. For any
HTTP method you want your resource to support, simply add an ``on_*()``
method to the class, where ``*`` is any one of the standard
HTTP methods, lowercased (e.g., ``on_get()``, ``on_put()``,
``on_head()``, etc.).

.. note::
    Supported HTTP methods are those specified in
    `RFC 7231 <https://tools.ietf.org/html/rfc7231>`_ and
    `RFC 5789 <https://tools.ietf.org/html/rfc5789>`_. This includes
    GET, HEAD, POST, PUT, DELETE, CONNECT, OPTIONS, TRACE, and PATCH.

We call these well-known methods "responders". Each responder takes (at
least) two params, one representing the HTTP request, and one representing
the HTTP response to that request. By convention, these are called
``req`` and ``resp``, respectively. Route templates and hooks can inject extra
params, as we shall see later on.

Right now, the image resource responds to GET requests with a simple
``200 OK`` and a JSON body. Falcon's Internet media type defaults to
``application/json`` but you can set it to whatever you like.
Noteworthy JSON alternatives include
`YAML <https://yaml.org/>`_ and `MessagePack <https://msgpack.org/>`_.

Next let's wire up this resource and see it in action. Go back to
``app.py`` and modify it so that it looks something like this:

.. literalinclude:: ../../examples/look/versions/03_app.py
    :language: python

Now, when a request comes in for ``/images``, Falcon will call the
responder on the images resource that corresponds to the requested
HTTP method.

Let's try it. Restart Gunicorn (unless you're using ``--reload``), and
send a GET request to the resource:

.. code:: bash

    $ http localhost:8000/images

You should receive a ``200 OK`` response, including a JSON-encoded
representation of the "images" resource.

.. note::

    ``add_route()`` expects an instance of the
    resource class, not the class itself. The same instance is used for
    all requests. This strategy improves performance and reduces memory
    usage, but this also means that if you host your application with a
    threaded web server, resources and their dependencies must be
    thread-safe.

We can use the :ref:`inspect` to visualize the application configuration:

.. code:: bash

    falcon-inspect-app look.app:app

This prints the following, correctly indicating that we are handling ``GET``
requests in the ``/images`` route:

.. code::

    Falcon App (WSGI)
    • Routes:
        ⇒ /images - Resource:
           └── GET - on_get

So far we have only implemented a responder for GET. Let's see what
happens when a different method is requested:

.. code:: bash

    $ http PUT localhost:8000/images

This time you should get back ``405 Method Not Allowed``,
since the resource does not support the ``PUT`` method. Note the
value of the Allow header:

.. code:: bash

    allow: GET, OPTIONS

This is generated automatically by Falcon based on the set of
methods implemented by the target resource. If a resource does not
include its own OPTIONS responder, the framework provides a
default implementation. Therefore, OPTIONS is always included in the
list of allowable methods.

.. note::

    If you have a lot of experience with other Python web frameworks,
    you may be used to using decorators to set up your routes. Falcon's
    particular approach provides the following benefits:

    * The URL structure of the application is centralized. This makes
      it easier to reason about and maintain the API over time.
    * The use of resource classes maps somewhat naturally to the REST
      architectural style, in which a URL is used to identify a resource
      only, not the action to perform on that resource.
    * Resource class methods provide a uniform interface that does not
      have to be reinvented (and maintained) from class to class and
      application to application.

Next, just for fun, let's modify our resource to use
`MessagePack <https://msgpack.org/>`_ instead of JSON. Start by
installing the relevant package:

.. code:: bash

    $ pip install msgpack-python

Then, update the responder to use the new media type:

.. literalinclude:: ../../examples/look/versions/04_images.py
    :language: python

Note the use of ``resp.data`` in lieu of ``resp.text``. If you assign a
bytestring to the latter, Falcon will figure it out, but you can
realize a small performance gain by assigning directly to ``resp.data``.

Also note the use of ``falcon.MEDIA_MSGPACK``. The ``falcon`` module
provides a number of constants for common media types, including
``falcon.MEDIA_JSON``, ``falcon.MEDIA_MSGPACK``, ``falcon.MEDIA_YAML``,
``falcon.MEDIA_XML``, ``falcon.MEDIA_HTML``, ``falcon.MEDIA_JS``,
``falcon.MEDIA_TEXT``, ``falcon.MEDIA_JPEG``, ``falcon.MEDIA_PNG``,
and ``falcon.MEDIA_GIF``.

Restart Gunicorn (unless you're using ``--reload``), and then try
sending a GET request to the revised resource:

.. code:: bash

    $ http localhost:8000/images

.. _testing_tutorial:

Testing your application
------------------------

Fully exercising your code is critical to creating a robust application.
Let's take a moment to write a test for what's been implemented so
far.

First, create a ``tests`` directory with ``__init__.py`` and a test
module (``test_app.py``) inside it. The project's structure should
now look like this:

.. code:: bash

    look
    ├── .venv
    ├── look
    │   ├── __init__.py
    │   ├── app.py
    │   └── images.py
    └── tests
        ├── __init__.py
        └── test_app.py

Falcon supports :ref:`testing <testing>` its :class:`~falcon.App` object by
simulating HTTP requests.

Tests can either be written using Python's standard :mod:`unittest`
module, or with any of a number of third-party testing
frameworks, such as `pytest <https://docs.pytest.org/>`_. For
this tutorial we'll use `pytest <https://docs.pytest.org/>`_
since it allows for more pythonic test code as compared to the
JUnit-inspired :mod:`unittest` module.

Let's start by installing the
`pytest <https://docs.pytest.org/>`_ package:

.. code:: bash

    $ pip install pytest

Next, edit ``test_app.py`` to look like this:

.. literalinclude:: ../../examples/look/versions/05_test_app.py
    :language: python

From the main project directory, exercise your new test by running
pytest against the ``tests`` directory:

.. code:: bash

    $ pytest tests

If pytest reports any errors, take a moment to fix them up before
proceeding to the next section of the tutorial.

Request and Response Objects
----------------------------

Each responder in a resource receives a ``Request`` object that can be
used to read the headers, query parameters, and body of the request. You
can use the standard ``help()`` function or IPython's magic ``?``
function to list the attributes and methods of Falcon's ``Request``
class:

.. code:: bash

    In [1]: import falcon

    In [2]: falcon.Request?

Each responder also receives a ``Response`` object that can be used for
setting the status code, headers, and body of the response:

.. code:: bash

    In [3]: falcon.Response?

This will be useful when creating a POST endpoint in the application
that can add new image resources to our collection. We'll tackle this
functionality next.

We'll use TDD this time around, to demonstrate how to apply this
particular testing strategy when developing a Falcon application. Via
tests, we'll first define precisely what we want the application to do,
and then code until the tests tell us that we're done.

.. note::
    To learn more about TDD, you may wish to check out one of the many
    books on the topic, such as
    `Test Driven Development with Python <https://www.obeythetestinggoat.com/pages/book.html>`_.
    The examples in this particular book use the Django framework and
    even JavaScript, but the author covers a number of testing
    principles that are widely applicable.

Let's start by adding an additional import statement to ``test_app.py``.
We need to import two modules from ``unittest.mock``:

.. code:: python

    from unittest.mock import mock_open, call

Now add the following test:

.. code:: python

    # "monkeypatch" is a special built-in pytest fixture that can be
    # used to install mocks.
    def test_posted_image_gets_saved(client, monkeypatch):
        mock_file_open = mock_open()
        monkeypatch.setattr('io.open', mock_file_open)

        fake_uuid = '123e4567-e89b-12d3-a456-426655440000'
        monkeypatch.setattr('uuid.uuid4', lambda: fake_uuid)

        # When the service receives an image through POST...
        fake_image_bytes = b'fake-image-bytes'
        response = client.simulate_post(
            '/images',
            body=fake_image_bytes,
            headers={'content-type': 'image/png'}
        )

        # ...it must return a 201 code, save the file, and return the
        # image's resource location.
        assert response.status == falcon.HTTP_CREATED
        assert call().write(fake_image_bytes) in mock_file_open.mock_calls
        assert response.headers['location'] == '/images/{}.png'.format(fake_uuid)

As you can see, this test relies heavily on mocking, making it
somewhat fragile in the face of implementation changes. We'll revisit
this later. For now, run the tests again and watch to make sure
they fail. A key step in the TDD workflow is verifying that
your tests **do not** pass before moving on to the implementation:

.. code:: bash

    $ pytest tests

To make the new test pass, we need to add a new method for handling
POSTs. Open ``images.py`` and add a POST responder to the
``Resource`` class as follows:

.. literalinclude:: ../../examples/look/versions/06_images.py
    :language: python

As you can see, we generate a unique name for the image, and then write
it out by reading from ``req.stream``. It's called ``stream`` instead
of ``body`` to emphasize the fact that you are really reading from an input
stream; by default Falcon does not spool or decode request data, instead
giving you direct access to the incoming binary stream provided by the
WSGI server.

Note the use of ``falcon.HTTP_201`` for setting the response status to
"201 Created". We could have also used the ``falcon.HTTP_CREATED``
alias. For a full list of predefined status strings, simply
call ``help()`` on ``falcon.status_codes``:

.. code:: bash

    In [4]: help(falcon.status_codes)

The last line in the ``on_post()`` responder sets the Location header for the
newly created resource. (We will create a route for that path in just a minute.)
The :class:`~falcon.Request` and :class:`~falcon.Response` classes contain
convenient attributes for reading and setting common headers, but you can always
access any header by name with the ``req.get_header()`` and
``resp.set_header()`` methods.

Take a moment to run pytest again to check your progress:

.. code:: bash

    $ pytest tests

You should see a ``TypeError`` as a consequence of adding the
``storage_path`` parameter to ``Resource.__init__()``.

To fix this, simply edit ``app.py`` and pass in a path to the
initializer. For now, just use the working directory from which you
started the service:

.. code:: python

    images = Resource(storage_path='.')

Try running the tests again. This time, they should pass with flying
colors!

.. code:: bash

    $ pytest tests

Finally, restart Gunicorn and then try
sending a POST request to the resource from the command line
(substituting ``test.png`` for a path to any PNG you like.)

.. code:: bash

    $ http POST localhost:8000/images Content-Type:image/png < test.png

Now, if you check your storage directory, it should contain a copy of the
image you just POSTed.

Upward and onward!

Refactoring for testability
---------------------------

Earlier we pointed out that our POST test relied heavily on mocking,
relying on assumptions that may or may not hold true as the code
evolves. To mitigate this problem, we'll not only have to refactor the
tests, but also the application itself.

We'll start by factoring out the business logic from the resource's
POST responder in ``images.py`` so that it can be tested independently.
In this case, the resource's "business logic" is simply the image-saving
operation:

.. literalinclude:: ../../examples/look/versions/07_images.py
    :language: python

Let's check to see if we broke anything with the changes above:

.. code:: bash

    $ pytest tests

Hmm, it looks like we forgot to update ``app.py``. Let's do that now:

.. literalinclude:: ../../examples/look/versions/08_app.py
    :language: python

Let's try again:

.. code:: bash

    $ pytest tests

Now you should see a failed test assertion regarding ``mock_file_open``.
To fix this, we need to switch our strategy from monkey-patching to
dependency injection. Return to ``app.py`` and modify it to look
similar to the following:

.. literalinclude:: ../../examples/look/versions/09_app.py
    :language: python

As you can see, the bulk of the setup logic has been moved to
``create_app()``, which can be used to obtain an App object either
for testing or for hosting in production.
``get_app()`` takes care of instantiating additional resources and
configuring the application for hosting.

The command to run the application is now:

.. code:: bash

    $ gunicorn --reload 'look.app:get_app()'

Finally, we need to update the test code. Modify ``test_app.py`` to
look similar to this:

.. literalinclude:: ../../examples/look/versions/10_test_app.py
    :language: python

As you can see, we've redone the POST. While there are fewer mocks, the assertions
have gotten more elaborate to properly check interactions at the interface boundaries.

Let's check our progress:

.. code:: bash

    $ pytest tests

All green! But since we used a mock, we're no longer covering the actual
saving of the image. Let's add a test for that:

.. code:: python

    def test_saving_image(monkeypatch):
        # This still has some mocks, but they are more localized and do not
        # have to be monkey-patched into standard library modules (always a
        # risky business).
        mock_file_open = mock_open()

        fake_uuid = '123e4567-e89b-12d3-a456-426655440000'
        def mock_uuidgen():
            return fake_uuid

        fake_image_bytes = b'fake-image-bytes'
        fake_request_stream = io.BytesIO(fake_image_bytes)
        storage_path = 'fake-storage-path'
        store = look.images.ImageStore(
            storage_path,
            uuidgen=mock_uuidgen,
            fopen=mock_file_open
        )

        assert store.save(fake_request_stream, 'image/png') == fake_uuid + '.png'
        assert call().write(fake_image_bytes) in mock_file_open.mock_calls

Now give it a try:

.. code:: bash

    $ pytest tests -k test_saving_image

Like the former test, this one still uses mocks. But the
structure of the code has been improved through the techniques of
componentization and dependency inversion, making the application
more flexible and testable.

.. tip::
    Checking code `coverage <https://coverage.readthedocs.io/>`_ would
    have helped us detect the missing test above; it's always a good
    idea to include coverage testing in your workflow to ensure you
    don't have any bugs hiding off somewhere in an unexercised code
    path.

Functional tests
----------------

Functional tests define the application's behavior from the outside.
When using TDD, this can be a more natural place to start as opposed
to lower-level unit testing, since it is difficult to anticipate
what internal interfaces and components are needed in advance of
defining the application's user-facing functionality.

In the case of the refactoring work from the last section, we could have
inadvertently introduced a functional bug into the application that our
unit tests would not have caught. This can happen when a bug is a result
of an unexpected interaction between multiple units, between
the application and the web server, or between the application and
any external services it depends on.

With test helpers such as ``simulate_get()`` and ``simulate_post()``,
we can create tests that span multiple units. But we can also go one
step further and run the application as a normal, separate process
(e.g. with Gunicorn). We can then write tests that interact with the running
process through HTTP, behaving like a normal client.

Let's see this in action. Create a new test module,
``tests/test_integration.py`` with the following contents:

.. literalinclude:: ../../examples/look/versions/11_test_integration.py
    :language: python

Next, install the ``requests`` package (as required by the new test)
and make sure Gunicorn is up and running:

.. code:: bash

    $ pip install requests
    $ gunicorn 'look.app:get_app()'

Then, in another terminal, try running the new test:

.. code:: bash

    $ pytest tests -k test_posted_image_gets_saved

The test will fail since it expects the image file to reside under
``/tmp``. To fix this, modify ``app.py`` to add the ability to configure
the image storage directory with an environment variable:

.. literalinclude:: ../../examples/look/versions/12_app.py
    :language: python

Now you can re-run the app against the desired storage directory:

.. code:: bash

    $ LOOK_STORAGE_PATH=/tmp gunicorn --reload 'look.app:get_app()'

You should now be able to re-run the test and see it succeed:

.. code:: bash

    $ pytest tests -k test_posted_image_gets_saved

.. note::
    The above process of starting, testing, stopping, and cleaning
    up after each test run can (and really should) be automated.
    Depending on your needs, you can develop your own automation
    fixtures, or use a library such as
    `mountepy <https://github.com/butla/mountepy>`_.

Many developers choose to write tests like the above to sanity-check
their application's primary functionality, while leaving the bulk of
testing to simulated requests and unit tests. These latter types
of tests generally execute much faster and facilitate more fine-grained
test assertions as compared to higher-level functional and system
tests. That being said, testing strategies vary widely and you should
choose the one that best suits your needs.

At this point, you should have a good grip on how to apply
common testing strategies to your Falcon application. For the
sake of brevity we'll omit further testing instructions from the
following sections, focusing instead on showcasing more of Falcon's
features.

.. _tutorial-serving-images:

Serving Images
--------------

Now that we have a way of getting images into the service, we of course
need a way to get them back out. What we want to do is return an image
when it is requested, using the path that came back in the Location
header.

Try executing the following:

.. code:: bash

    $ http localhost:8000/images/db79e518-c8d3-4a87-93fe-38b620f9d410.png

In response, you should get a ``404 Not Found``. This is the default
response given by Falcon when it can not find a resource that matches
the requested URL path.

Let's address this by creating a separate class to represent a single
image resource. We will then add an ``on_get()`` method to respond to
the path above.

Go ahead and edit your ``images.py`` file to look something like this:

.. literalinclude:: ../../examples/look/versions/13_images.py
    :language: python

As you can see, we renamed ``Resource`` to ``Collection`` and added a new ``Item``
class to represent a single image resource. Alternatively, these two classes could
be consolidated into one by using suffixed responders. (See also:
:meth:`~falcon.App.add_route`)

Also, note the ``name`` parameter for the ``on_get()`` responder. Any URI
parameters that you specify in your routes will be turned into corresponding
kwargs and passed into the target responder as such. We'll see how to specify
URI parameters in a moment.

Inside the ``on_get()`` responder,
we set the Content-Type header based on the filename extension, and then
stream out the image directly from an open file handle. Note the use of
``resp.content_length``. Whenever using ``resp.stream`` instead of ``resp.text`` or
``resp.data``, you typically also specify the expected length of the stream using the
Content-Length header, so that the web client knows how much data to read from the response.

.. note:: If you do not know the size of the stream in advance, you can work around
   that by using chunked encoding, but that's beyond the scope of this
   tutorial.

If ``resp.status`` is not set explicitly, it defaults to ``200 OK``, which is
exactly what we want ``on_get()`` to do.

Now let's wire everything up and give it a try. Edit ``app.py`` to look
similar to the following:

.. literalinclude:: ../../examples/look/look/app.py
    :language: python

As you can see, we specified a new route, ``/images/{name}``. This causes
Falcon to expect all associated responders to accept a ``name``
argument.

.. note::

    Falcon also supports more complex parameterized path segments that
    contain multiple values. For example, a version control API might
    use the following route template for diffing two code branches::

        /repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}

Now re-run your app and try to POST another picture:

.. code:: bash

    $ http POST localhost:8000/images Content-Type:image/png < test.png

Make a note of the path returned in the Location header, and use it to
GET the image:

.. code:: bash

    $ http localhost:8000/images/dddff30e-d2a6-4b57-be6a-b985ee67fa87.png

HTTPie won't display the image, but you can see that the
response headers were set correctly. Just for fun, go ahead and paste
the above URI into your browser. The image should display correctly.

Inspecting the application now returns:

.. code:: bash

    falcon-inspect-app look.app:get_app

.. code::

    Falcon App (WSGI)
    • Routes:
        ⇒ /images - Collection:
           ├── GET - on_get
           └── POST - on_post
        ⇒ /images/{name} - Item:
           └── GET - on_get

Query Strings
-------------
Now that we are able to get the images from the service, we need a way to get
a list of available images. We have already set up this route. Before testing this
route let's change its output format back to JSON to have a more
terminal-friendly output. The top of file ``images.py`` should look like this:

.. code:: python

    import io
    import os
    import re
    import uuid
    import mimetypes

    import falcon
    import json


    class Collection:

        def __init__(self, image_store):
            self._image_store = image_store

        def on_get(self, req, resp):
            # TODO: Modify this to return a list of href's based on
            # what images are actually available.
            doc = {
                'images': [
                    {
                        'href': '/images/1eaf6ef1-7f2d-4ecc-a8d5-6e8adba7cc0e.png'
                    }
                ]
            }

            resp.text = json.dumps(doc, ensure_ascii=False)
            resp.status = falcon.HTTP_200

    def on_post(self, req, resp):
        name = self._image_store.save(req.stream, req.content_type)
        resp.status = falcon.HTTP_201
        resp.location = '/images/' + name

Now try the following:

.. code:: bash

    http localhost:8000/images

In response you should get the following data that we statically have put in the code.

.. code::

    {
        "images": [
            {
                "href": "/images/1eaf6ef1-7f2d-4ecc-a8d5-6e8adba7cc0e.png"
            }
        ]
    }

Let's go back to the ``on_get`` method and create a dynamic response. We can
use query strings to set maximum image size and get the list of all images
smaller than the specified value. We will use method ``get_param_as_int`` to
set a default value of ``-1`` in case no ``maxsize`` query string was provided
and also to enable a minimum value validation.

.. literalinclude:: ../../examples/look/versions/14_images.py
    :language: python

As you can see the method ``list`` has been added to ``ImageStore`` in order
to return list of available images smaller than ``max_size`` unless it is not
``-1``, in which case it will behave like there was no predicament of image size.
Let's try to save some binary data as images in the service and then try to
retrieve their list. Execute the following commands in order to simulate the
creation of 3 files as images with different sizes. While these are not valid
PNG files, they will work for this tutorial.

.. code:: bash

   echo "First Case" > pseudo-image-1.png
   echo "Second Case" > pseudo-image-2.png
   echo "3rd Case" > pseudo-image-3.png

Now we need to store these files using ``POST`` request:

.. code:: bash

   http POST localhost:8000/images Content-Type:image/png < pseudo-image-1.png
   http POST localhost:8000/images Content-Type:image/png < pseudo-image-2.png
   http POST localhost:8000/images Content-Type:image/png < pseudo-image-3.png

If we check the size of these files, we will see that they are 11, 12, 9 bytes
respectively. Let's try to get the list of the images which are smaller or
equal to 11 bytes.

.. code:: bash

   http localhost:8000/images?maxsize=11

We expect to get a list of 2 files, which will be similar to the following:

.. code::

    {
        "images": [
            {
                "href": "/images/7ba2ebc9-726f-46b0-9615-a69824f5089b.png"
            },
            {
                "href": "/images/e4354a31-2161-4064-805c-3bc7c332e7e6.png"
            }
        ]
    }

You could also now validate the response with getting the image files using
the ``href`` value in the response and compare them with the original files.


Introducing Hooks
-----------------

At this point you should have a pretty good understanding of the basic parts
that make up a Falcon-based API. Before we finish up, let's just take a few
minutes to clean up the code and add some error handling.

First, let's check the incoming media type when something is posted
to make sure it is a common image type. We'll implement this with a
``before`` hook.

Start by defining a list of media types the service will accept. Place
this constant near the top, just after the import statements in
``images.py``:

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
            raise falcon.HTTPBadRequest(title='Bad request', description=msg)

And then attach the hook to the ``on_post()`` responder:

.. code:: python

    @falcon.before(validate_image_type)
    def on_post(self, req, resp):
        pass

Now, before every call to that responder, Falcon will first invoke
``validate_image_type()``. There isn't anything special about this
function, other than it must accept four arguments. Every hook takes, as its
first two arguments, a reference to the same ``req`` and ``resp`` objects
that are passed into responders. The ``resource`` argument is a Resource
instance associated with the request. The fourth argument, named ``params``
by convention, is a reference to the kwarg dictionary Falcon creates for
each request. ``params`` will contain the route's URI template params and
their values, if any.

As you can see in the example above, you can use ``req`` to get information
about the incoming request. However, you can also use ``resp`` to play with
the HTTP response as needed, and you can even use hooks to inject extra
kwargs:

.. code:: python

    def extract_project_id(req, resp, resource, params):
        """Adds `project_id` to the list of params for all responders.

        Meant to be used as a `before` hook.
        """
        params['project_id'] = req.get_header('X-PROJECT-ID')

Now, you might imagine that such a hook should apply to all responders
for a resource. In fact, hooks can be applied to an entire resource
by simply decorating the class:

.. code:: python

    @falcon.before(extract_project_id)
    class Message:
        pass

Similar logic can be applied globally with middleware.
(See also: :ref:`falcon.middleware <middleware>`)

Now that you've added a hook to validate the media type, you can see it
in action by attempting to POST something nefarious:

.. code:: bash

    $ http POST localhost:8000/images Content-Type:image/jpx

You should get back a ``400 Bad Request`` status and a nicely structured
error body.

.. tip::
    When something goes wrong, you usually want to give your users
    some info to help them resolve the issue. The exception to this rule
    is when an error occurs because the user is requested something they
    are not authorized to access. In that case, you may wish to simply
    return ``404 Not Found`` with an empty body, in case a malicious
    user is fishing for information that will help them crack your app.

Check out the :ref:`hooks reference <hooks>` to learn more.

Error Handling
--------------

Generally speaking, Falcon assumes that resource responders
(``on_get()``, ``on_post()``, etc.) will, for the most part, do the
right thing. In other words, Falcon doesn't try very hard to protect
responder code from itself.

This approach reduces the number of (often) extraneous checks that Falcon
would otherwise have to perform, making the framework more efficient. With
that in mind, writing a high-quality API based on Falcon requires that:

1. Resource responders set response variables to sane values.
2. Untrusted input (i.e., input from an external client or service) is
   validated.
3. Your code is well-tested, with high code coverage.
4. Errors are anticipated, detected, logged, and handled appropriately
   within each responder or by global error handling hooks.

When it comes to error handling, you can always directly set the error
status, appropriate response headers, and error body using the ``resp``
object. However, Falcon tries to make things a little easier by
providing a :ref:`set of error classes <predefined_errors>` you can
raise when something goes wrong. Falcon will convert any instance or
subclass of :class:`falcon.HTTPError` raised by a responder, hook, or
middleware component into an appropriate HTTP response.

You may raise an instance of :class:`falcon.HTTPError` directly, or use
any one of a number of :ref:`predefined errors <predefined_errors>`
that are designed to set the response headers and body appropriately
for each error type.

.. tip::
    Error handlers may be registered for any type, including
    :class:`~.HTTPError`. This feature provides a central location
    for logging and otherwise handling exceptions raised by
    responders, hooks, and middleware components.

    See also: :meth:`~.falcon.App.add_error_handler`.

Let's see a quick example of how this works. Try requesting an invalid
image name from your application:

.. code:: bash

    $ http localhost:8000/images/voltron.png

As you can see, the result isn't exactly graceful. To fix this, we'll
need to add some exception handling. Modify your ``Item`` class
as follows:

.. code:: python

    class Item:

        def __init__(self, image_store):
            self._image_store = image_store

        def on_get(self, req, resp, name):
            resp.content_type = mimetypes.guess_type(name)[0]

            try:
                resp.stream, resp.content_length = self._image_store.open(name)
            except OSError:
                # Normally you would also log the error.
                raise falcon.HTTPNotFound()

Now let's try that request again:

.. code:: bash

    $ http localhost:8000/images/voltron.png

Additional information about error handling is available in the
:ref:`error handling reference <errors>`.

What Now?
---------

Our friendly community is available to answer your questions and help you
work through sticky problems. See also: :ref:`Getting Help <help>`.

As mentioned previously, Falcon's docstrings are quite extensive, and so you
can learn a lot just by poking around Falcon's modules from a Python REPL,
such as `IPython <https://ipython.org/>`_ or
`bpython <https://bpython-interpreter.org/>`_.

Also, don't be shy about pulling up Falcon's source code on GitHub or in your
favorite text editor. The team has tried to make the code as straightforward
and readable as possible; where other documentation may fall short, the code
basically can't be wrong.

A number of Falcon add-ons, templates, and complementary packages are
available for use in your projects. We've listed several of these on the
`Falcon wiki <https://github.com/falconry/falcon/wiki>`_ as a starting
point, but you may also wish to search PyPI for additional resources.
