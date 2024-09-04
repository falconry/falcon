.. _tutorial-asgi:

Tutorial (ASGI)
===============

In this tutorial we'll walk through building an API for a simple image sharing
service. Along the way, we'll discuss the basic anatomy of an asynchronous
Falcon application: responders, routing, middleware, executing synchronous
functions in an executor, and more!

.. note::
   This tutorial covers the asynchronous flavor of Falcon using
   the `ASGI <https://asgi.readthedocs.io/en/latest/>`__ protocol.

   Synchronous (`WSGI <https://www.python.org/dev/peps/pep-3333/>`__) Falcon
   application development is covered in our :ref:`WSGI tutorial<tutorial>`.

   New Falcon users may also want to choose the WSGI flavor to familiarize
   themselves with Falcon's basic concepts.

First Steps
-----------

Let's start by creating a fresh environment and the corresponding project
directory structure, along the lines of :ref:`tutorial-first-steps` from the
WSGI tutorial::

  asgilook
  ├── .venv
  └── asgilook
      ├── __init__.py
      └── app.py

We'll create a *virtualenv* using the ``venv`` module from the standard library
(Falcon requires Python 3.8+)::

  $ mkdir asgilook
  $ python3 -m venv asgilook/.venv
  $ source asgilook/.venv/bin/activate

.. note::
   If your Python distribution does not happen to include the ``venv`` module,
   you can always install and use `virtualenv <https://virtualenv.pypa.io/>`_
   instead.

.. tip::
   Some of us find it convenient to manage *virtualenv*\s with
   `virtualenvwrapper <https://virtualenvwrapper.readthedocs.io>`_ or
   `pipenv <https://pipenv.pypa.io/>`_,
   particularly when it comes to hopping between several environments.

Next, :ref:`install Falcon <install>` into your *virtualenv*::

  $ pip install falcon

You can then create a basic :class:`Falcon ASGI application <falcon.asgi.App>`
by adding an ``asgilook/app.py`` module with the following contents:

.. code:: python

   import falcon.asgi

   app = falcon.asgi.App()

As in the :ref:`WSGI tutorial's introduction <tutorial-first-steps>`,
let's not forget to mark ``asgilook`` as a Python package:

.. code:: bash

    $ touch asgilook/__init__.py

Hosting Our App
---------------

For running our async application, we'll need an
`ASGI <https://asgi.readthedocs.io/>`_ application server. Popular choices
include:

* `Uvicorn <https://www.uvicorn.org/>`_
* `Daphne <https://github.com/django/daphne/>`_
* `Hypercorn <https://github.com/pgjones/hypercorn/>`_

For a simple tutorial application like ours, any of the above should do.
Let's pick the popular ``uvicorn`` for now::

  $ pip install uvicorn

See also: :ref:`ASGI Server Installation <install_asgi_server>`.

While we're at it, let's install the handy
`HTTPie <https://github.com/jakubroztocil/httpie>`_ HTTP client to help us
exercise our app::

  $ pip install httpie

Now let's try loading our application::

  $ uvicorn asgilook.app:app
  INFO:     Started server process [2020]
  INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
  INFO:     Waiting for application startup.
  INFO:     Application startup complete.

We can verify it works by trying to access the URL provided above by
``uvicorn``::

  $ http http://127.0.0.1:8000
  HTTP/1.1 404 Not Found
  content-length: 0
  content-type: application/json
  date: Sun, 05 Jul 2020 13:37:01 GMT
  server: uvicorn

Woohoo, it works!!!

Well, sort of. Onwards to adding some real functionality!

.. _asgi_tutorial_config:

Configuration
-------------

Next, let's make our app configurable by allowing the user to modify the file
system path where images are stored. We'll also allow the UUID generator to be
customized.

As Falcon does not prescribe a specific configuration library or strategy, we
are free to choose our own adventure (see also a related question in our
FAQ: :ref:`configuration-approaches`).

In this tutorial, we'll just pass around a ``Config`` instance to resource
initializers for easier testing (coming later in this tutorial). Create a new
module, ``config.py`` next to ``app.py``, and add the following code to it:

.. code:: python

    import os
    import pathlib
    import uuid


    class Config:
        DEFAULT_CONFIG_PATH = '/tmp/asgilook'
        DEFAULT_UUID_GENERATOR = uuid.uuid4

        def __init__(self):
            self.storage_path = pathlib.Path(
                os.environ.get('ASGI_LOOK_STORAGE_PATH', self.DEFAULT_CONFIG_PATH))
            self.storage_path.mkdir(parents=True, exist_ok=True)

            self.uuid_generator = Config.DEFAULT_UUID_GENERATOR

Image Store
-----------

Since we are going to read and write image files, care must be taken to
avoid blocking the app during I/O. We'll give ``aiofiles`` a try::

  pip install aiofiles

In addition, let's twist the original WSGI "Look" design a bit, and convert
all uploaded images to JPEG with the popular
`Pillow <https://pillow.readthedocs.io/>`_ library::

  pip install Pillow

We can now implement a basic async image store. Save the following code as
``store.py`` next to ``app.py`` and ``config.py``:

.. code:: python

    import asyncio
    import datetime
    import io

    import aiofiles
    import PIL.Image

    import falcon


    class Image:
        def __init__(self, config, image_id, size):
            self._config = config

            self.image_id = image_id
            self.size = size
            self.modified = datetime.datetime.now(datetime.timezone.utc)

        @property
        def path(self):
            return self._config.storage_path / self.image_id

        @property
        def uri(self):
            return f'/images/{self.image_id}.jpeg'

        def serialize(self):
            return {
                'id': self.image_id,
                'image': self.uri,
                'modified': falcon.dt_to_http(self.modified),
                'size': self.size,
            }


    class Store:
        def __init__(self, config):
            self._config = config
            self._images = {}

        def _load_from_bytes(self, data):
            return PIL.Image.open(io.BytesIO(data))

        def _convert(self, image):
            rgb_image = image.convert('RGB')

            converted = io.BytesIO()
            rgb_image.save(converted, 'JPEG')
            return converted.getvalue()

        def get(self, image_id):
            return self._images.get(image_id)

        def list_images(self):
            return sorted(self._images.values(), key=lambda item: item.modified)

        async def save(self, image_id, data):
            loop = asyncio.get_running_loop()
            image = await loop.run_in_executor(None, self._load_from_bytes, data)
            converted = await loop.run_in_executor(None, self._convert, image)

            path = self._config.storage_path / image_id
            async with aiofiles.open(path, 'wb') as output:
                await output.write(converted)

            stored = Image(self._config, image_id, image.size)
            self._images[image_id] = stored
            return stored

Here we store data using ``aiofiles``, and run ``Pillow`` image transformation
functions in the default :class:`~concurrent.futures.ThreadPoolExecutor`,
hoping that at least some of these image operations release the GIL during
processing.

.. note::
  The :class:`~concurrent.futures.ProcessPoolExecutor` is another alternative
  for long running tasks that do not release the GIL, such as CPU-bound pure
  Python code. Note, however, that
  :class:`~concurrent.futures.ProcessPoolExecutor` builds upon the
  :mod:`multiprocessing` module, and thus inherits its caveats: higher
  synchronization overhead, and the requirement for the task and its arguments
  to be picklable (which also implies that the task must be reachable from the
  global namespace, i.e., an anonymous ``lambda`` simply won't work).

.. _asgi_tutorial_image_resources:

Images Resource(s)
------------------

In the ASGI flavor of Falcon, all responder methods, hooks and middleware
methods must be awaitable coroutines. Let's see how this works by
implementing a resource to represent both a single image and a collection
of images. Place the code below in a file named ``images.py``:

.. code:: python

    import aiofiles

    import falcon


    class Images:
        def __init__(self, config, store):
            self._config = config
            self._store = store

        async def on_get(self, req, resp):
            resp.media = [image.serialize() for image in self._store.list_images()]

        async def on_get_image(self, req, resp, image_id):
            # NOTE: image_id: UUID is converted back to a string identifier.
            image = self._store.get(str(image_id))
            resp.stream = await aiofiles.open(image.path, 'rb')
            resp.content_type = falcon.MEDIA_JPEG

        async def on_post(self, req, resp):
            data = await req.stream.read()
            image_id = str(self._config.uuid_generator())
            image = await self._store.save(image_id, data)

            resp.location = image.uri
            resp.media = image.serialize()
            resp.status = falcon.HTTP_201

This module is an example of a Falcon "resource" class, as described in
:ref:`routing`. Falcon uses resource-based routing to encourage a RESTful
architectural style. For each HTTP method that a resource supports, the
target resource class simply implements a corresponding Python method with a
name that starts with ``on_`` and ends in the lowercased HTTP method name (e.g.,
``on_get()``, ``on_patch()``, ``on_delete()``, etc.)

.. note::
  If a Python method is omitted for a given HTTP verb, the framework will
  automatically respond with ``405 Method Not Allowed``. Falcon also provides
  a default responder for OPTIONS requests that takes into account which
  methods are implemented for the target resource.

Here we opted to implement support for both a single image (which supports
``GET`` for downloading the image) and a collection of images (which supports
``GET`` for listing the collection, and ``POST`` for uploading a new image) in
the same Falcon resource class. In order to make this work, the Falcon router
needs a way to determine which methods to call for the collection vs. the item.
This is done by using a suffixed route, as described in
:meth:`~falcon.asgi.App.add_route` (see also:
:ref:`collection-vs-item-routing`).

Alternatively, we could have split the implementation to strictly represent one
RESTful resource per class. In that case, there would have been no need to use
suffixed responders. Depending on the application, using two classes instead of
one may lead to a cleaner design. (See also: :ref:`recommended-route-layout`)

.. note::
    In this example, we serve the image by simply assigning an open
    ``aiofiles`` file to :attr:`resp.stream <falcon.asgi.Response.stream>`.
    This works because Falcon includes special handling for streaming async
    file-like objects.

.. warning::
    In production deployment, serving files directly from the web server,
    rather than through the Falcon ASGI app, will likely be more efficient, and
    therefore should be preferred. See also: :ref:`faq_static_files`

Also worth noting is that the ``on_get_image()`` responder will be receiving an
``image_id`` of type :class:`~uuid.UUID`. So what's going on here? How will the
``image_id`` field, matched from a string path segment, become a
:class:`~uuid.UUID`?

Falcon's default router supports simple validation and transformation using
:ref:`field converters <routing_field_converters>`. In this example, we'll use
the :class:`~falcon.routing.UUIDConverter` to validate the ``image_id`` input as
:class:`~uuid.UUID`. Converters are specified for a route by including their
:ref:`shorthand identifiers <routing_builtin_converters>` in the URI template
for the route; for instance, the route corresponding to ``on_get_image()`` will
use the following template (see also the next chapter, as well as
:ref:`routing`)::

    /images/{image_id:uuid}.jpeg

Since our application is still internally centered on string identifiers, feel
free to experiment with refactoring the image ``Store`` to use
:class:`~uuid.UUID`\s natively!

(Alternatively, one could implement a
:ref:`custom field converter <routing_custom_converters>` to use ``uuid`` only
for validation, but return an unmodified string.)

.. note::
    In contrast to asynchronous building blocks (responders, middleware, hooks
    etc.) of a Falcon ASGI application, field converters are simple synchronous
    data transformation functions that are not expected to perform any I/O.

Running Our Application
-----------------------

Now we're ready to configure the routes for our app to map image paths in the
request URL to an instance of our resource class.

Let's also refactor our ``app.py`` module to let us invoke ``create_app()``
wherever we need it. This will become useful later on when we start writing
test cases.

Modify ``app.py`` to read as follows:

.. code:: python

    import falcon.asgi

    from .config import Config
    from .images import Images
    from .store import Store


    def create_app(config=None):
        config = config or Config()
        store = Store(config)
        images = Images(config, store)

        app = falcon.asgi.App()
        app.add_route('/images', images)
        app.add_route('/images/{image_id:uuid}.jpeg', images, suffix='image')

        return app

As mentioned earlier, we need to use a route suffix for the ``Images`` class to
distinguish between a GET for a single image vs. the entire collection of
images.

Here, we map the ``'/images/{image_id:uuid}.jpeg'`` URI template to a
single image resource. By specifying an ``'image'`` suffix, we cause the
framework to look for responder methods that have names ending in ``'_image'``
(e.g, ``on_get_image()``).

We also specify the ``uuid`` field converter as discussed in the previous
section.

In order to bootstrap an ASGI app instance for ``uvicorn`` to reference, we'll
create a simple ``asgi.py`` module with the following contents:

.. literalinclude:: ../../examples/asgilook/asgilook/asgi.py
    :language: python

Running the application is not too dissimilar from the previous command line::

  $ uvicorn asgilook.asgi:app

Provided ``uvicorn`` is started as per the above command line, let's try
uploading some images in a separate terminal (change the picture path below
to point to an existing file)::

  $ http POST localhost:8000/images @/home/user/Pictures/test.png

  HTTP/1.1 201 Created
  content-length: 173
  content-type: application/json
  date: Tue, 24 Dec 2019 17:32:18 GMT
  location: /images/5cfd9fb6-259a-4c72-b8b0-5f4c35edcd3c.jpeg
  server: uvicorn

  {
      "id": "5cfd9fb6-259a-4c72-b8b0-5f4c35edcd3c",
      "image": "/images/5cfd9fb6-259a-4c72-b8b0-5f4c35edcd3c.jpeg",
      "modified": "Tue, 24 Dec 2019 17:32:19 GMT",
      "size": [
          462,
          462
      ]
  }

Next, try retrieving the uploaded image::

  $ http localhost:8000/images/5cfd9fb6-259a-4c72-b8b0-5f4c35edcd3c.jpeg

  HTTP/1.1 200 OK
  content-type: image/jpeg
  date: Tue, 24 Dec 2019 17:34:53 GMT
  server: uvicorn
  transfer-encoding: chunked

  +-----------------------------------------+
  | NOTE: binary data not shown in terminal |
  +-----------------------------------------+

We could also open the link in a web browser or pipe it to an image viewer
to verify that the image was successfully converted to a JPEG.

Let's check the image collection now::

  $ http localhost:8000/images

  HTTP/1.1 200 OK
  content-length: 175
  content-type: application/json
  date: Tue, 24 Dec 2019 17:36:31 GMT
  server: uvicorn

  [
      {
          "id": "5cfd9fb6-259a-4c72-b8b0-5f4c35edcd3c",
          "image": "/images/5cfd9fb6-259a-4c72-b8b0-5f4c35edcd3c.jpeg",
          "modified": "Tue, 24 Dec 2019 17:32:19 GMT",
          "size": [
              462,
              462
          ]
      }
  ]

The application file layout should now look like this::

  asgilook
  ├── .venv
  └── asgilook
      ├── __init__.py
      ├── app.py
      ├── asgi.py
      ├── config.py
      ├── images.py
      └── store.py

Dynamic Thumbnails
------------------

Let's pretend our image service customers want to render images in multiple
resolutions, for instance, as ``srcset`` for responsive HTML images or other
purposes.

Let's add a new method ``Store.make_thumbnail()`` to perform scaling on the
fly:

.. code:: python

    async def make_thumbnail(self, image, size):
        async with aiofiles.open(image.path, 'rb') as img_file:
            data = await img_file.read()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._resize, data, size)

We'll also add an internal helper to run the ``Pillow`` thumbnail operation that
is offloaded to a threadpool executor, again, in hoping that Pillow can release
the GIL for some operations:

.. code:: python

    def _resize(self, data, size):
        image = PIL.Image.open(io.BytesIO(data))
        image.thumbnail(size)

        resized = io.BytesIO()
        image.save(resized, 'JPEG')
        return resized.getvalue()

The ``store.Image`` class can be extended to also return URIs to thumbnails:

.. code:: python

    def thumbnails(self):
        def reductions(size, min_size):
            width, height = size
            factor = 2
            while width // factor >= min_size and height // factor >= min_size:
                yield (width // factor, height // factor)
                factor *= 2

        return [
            f'/thumbnails/{self.image_id}/{width}x{height}.jpeg'
            for width, height in reductions(
                self.size, self._config.min_thumb_size)]

Here, we only generate URIs for a series of downsized resolutions. The actual
scaling will happen on the fly upon requesting these resources.

Each thumbnail in the series is approximately half the size (one quarter
area-wise) of the previous one, similar to how
`mipmapping <https://en.wikipedia.org/wiki/Mipmap>`_ works in computer graphics.
You may wish to experiment with this resolution distribution.

After updating ``store.py``, the module should now look like this:

.. literalinclude:: ../../examples/asgilook/asgilook/store.py
    :language: python

Furthermore, it is practical to impose a minimum resolution, as any potential
benefit from switching between very small thumbnails (a few kilobytes each) is
likely to be overshadowed by the request overhead. As you may have noticed in
the above snippet, we are referencing this lower size limit as
``self._config.min_thumb_size``.
The :ref:`app configuration <asgi_tutorial_config>` will need to be updated
to add the ``min_thumb_size`` option (by default initialized to 64 pixels)
as follows:

.. code:: python

    import os
    import pathlib
    import uuid


    class Config:
        DEFAULT_CONFIG_PATH = '/tmp/asgilook'
        DEFAULT_MIN_THUMB_SIZE = 64
        DEFAULT_UUID_GENERATOR = uuid.uuid4

        def __init__(self):
            self.storage_path = pathlib.Path(
                os.environ.get('ASGI_LOOK_STORAGE_PATH', self.DEFAULT_CONFIG_PATH))
            self.storage_path.mkdir(parents=True, exist_ok=True)

            self.uuid_generator = Config.DEFAULT_UUID_GENERATOR
            self.min_thumb_size = self.DEFAULT_MIN_THUMB_SIZE

Let's also add a ``Thumbnails`` resource to expose the new
functionality. The final version of ``images.py`` reads:

.. literalinclude:: ../../examples/asgilook/asgilook/images.py
    :language: python

.. note::
  Even though we are only building a sample application, it is a good idea to
  cultivate a habit of making your code secure by design and secure by default.

  In this case, we see that generating thumbnails on the fly, based on
  arbitrary dimensions embedded in the URI, could easily be abused to
  create a denial-of-service attack.

  This particular attack is mitigated by validating the input (in this case, the
  requested path) against a list of allowed values.

Finally, a new thumbnail :meth:`route <falcon.asgi.App.add_route>` needs to
be added in ``app.py``. This step is left as an exercise for the reader.

.. tip::
    Draw inspiration from the thumbnail URI formatting string:

        .. code:: python

            f'/thumbnails/{self.image_id}/{width}x{height}.jpeg'

    The actual URI template for the thumbnails route should look quite similar
    to the above.

    Remember that we want to use the
    :class:`uuid <falcon.routing.UUIDConverter>` converter for the ``image_id``
    field, and image dimensions (``width`` and ``height``) should ideally be
    converted to :class:`int <falcon.routing.IntConverter>`\s.

(If you get stuck, see the final version of ``app.py`` later in this tutorial.)

.. note::
    If you try to request a non-existent resource (e.g., due to a missing route
    , or simply a typo in the URI), the framework will
    automatically render an ``HTTP 404 Not Found`` response by raising an
    instance of :class:`~falcon.HTTPNotFound` (unless that exception is
    intercepted by a
    :meth:`custom error handler <falcon.asgi.App.add_error_handler>`, or if the
    path matches a sink prefix).

    Conversely, if a route is matched to a resource, but there is no responder
    for the HTTP method in question, Falcon will render
    ``HTTP 405 Method Not Allowed`` via :class:`~falcon.HTTPMethodNotAllowed`.

The new ``thumbnails`` end-point should now render thumbnails on the fly::

  $ http POST localhost:8000/images @/home/user/Pictures/test.png

  HTTP/1.1 201 Created
  content-length: 319
  content-type: application/json
  date: Tue, 24 Dec 2019 18:58:20 GMT
  location: /images/f2375273-8049-4b10-b17e-8851db9ac7af.jpeg
  server: uvicorn

  {
      "id": "f2375273-8049-4b10-b17e-8851db9ac7af",
      "image": "/images/f2375273-8049-4b10-b17e-8851db9ac7af.jpeg",
      "modified": "Tue, 24 Dec 2019 18:58:21 GMT",
      "size": [
          462,
          462
      ],
      "thumbnails": [
          "/thumbnails/f2375273-8049-4b10-b17e-8851db9ac7af/231x231.jpeg",
          "/thumbnails/f2375273-8049-4b10-b17e-8851db9ac7af/115x115.jpeg"
      ]
  }


  $ http localhost:8000/thumbnails/f2375273-8049-4b10-b17e-8851db9ac7af/115x115.jpeg

  HTTP/1.1 200 OK
  content-length: 2985
  content-type: image/jpeg
  date: Tue, 24 Dec 2019 19:00:14 GMT
  server: uvicorn

  +-----------------------------------------+
  | NOTE: binary data not shown in terminal |
  +-----------------------------------------+

Again, we could also verify thumbnail URIs in the browser or image viewer that
supports HTTP input.

.. _asgi_tutorial_caching:

Caching Responses
-----------------

Although scaling thumbnails on-the-fly sounds cool, and we also avoid many pesky
small files littering our storage, it consumes CPU resources, and we would
soon find our application crumbling under load.

Let's mitigate this problem with response caching. We'll use Redis, taking
advantage of `redis <https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html>`_ for async
support::

  pip install redis

We will also need to serialize response data (the ``Content-Type`` header and
the body in the first version); ``msgpack`` should do::

  pip install msgpack

Our application will obviously need access to a Redis server. Apart from just
installing Redis server on your machine, one could also:

* Spin up Redis in Docker, eg::

    docker run -p 6379:6379 redis/redis-stack:latest

* Assuming Redis is installed on the machine, one could also try
  `pifpaf <https://github.com/jd/pifpaf>`_ for spinning up Redis just
  temporarily for ``uvicorn``::

    pifpaf run redis -- uvicorn asgilook.asgi:app

We will perform caching with a Falcon :ref:`middleware` component. Again, note
that all middleware callbacks must be asynchronous. Even calling ``ping()`` and
``close()`` on the Redis connection must be ``await``\ed. But how can we
``await`` coroutines from within our synchronous ``create_app()`` function?

`ASGI application lifespan events
<https://asgi.readthedocs.io/en/latest/specs/lifespan.html>`_ come to the
rescue. An ASGI application server emits these events upon application startup
and shutdown.

Let's implement the ``process_startup()`` and ``process_shutdown()`` handlers
in our middleware to execute code upon our application's startup and shutdown,
respectively:

.. code:: python

    async def process_startup(self, scope, event):
        await self._redis.ping()

    async def process_shutdown(self, scope, event):
        await self._redis.close()

.. warning::
    The Lifespan Protocol is an optional extension; please check if your ASGI
    server of choice implements it.

    ``uvicorn`` (that we picked for this tutorial) supports Lifespan.

At minimum, our middleware will need to know the Redis host(s) to use.
Let's also make our Redis connection factory
configurable to afford injecting different Redis client
implementations for production and testing.

.. note::
    Rather than requiring the caller to pass the host to the connection
    factory, a wrapper method could be used to implicitly reference
    ``self.redis_host``. Such a design might prove helpful for apps that
    need to create client connections in more than one place.

Assuming we call our new :ref:`configuration <asgi_tutorial_config>` item
``redis_host`` the final version of ``config.py`` now reads:

.. literalinclude:: ../../examples/asgilook/asgilook/config.py
    :language: python

Let's complete the Redis cache component by implementing
two more middleware methods, in addition to ``process_startup()`` and
``process_shutdown()``. Create a ``cache.py`` module containing the following
code:

.. literalinclude:: ../../examples/asgilook/asgilook/cache.py
    :language: python

For caching to take effect, we also need to modify ``app.py`` to add
the ``RedisCache`` component to our application's middleware list.
The final version of ``app.py`` should look something like this:

.. literalinclude:: ../../examples/asgilook/asgilook/app.py
    :language: python

Now, subsequent access to ``/thumbnails`` should be cached, as indicated by the
``x-asgilook-cache`` header::

  $ http localhost:8000/thumbnails/167308e4-e444-4ad9-88b2-c8751a4e37d4/115x115.jpeg

  HTTP/1.1 200 OK
  content-length: 2985
  content-type: image/jpeg
  date: Tue, 24 Dec 2019 19:46:51 GMT
  server: uvicorn
  x-asgilook-cache: Hit

  +-----------------------------------------+
  | NOTE: binary data not shown in terminal |
  +-----------------------------------------+

.. note::
   Left as another exercise for the reader: individual images are streamed
   directly from ``aiofiles`` instances, and caching therefore does not work
   for them at the moment.

The project's structure should now look like this::

  asgilook
  ├── .venv
  └── asgilook
      ├── __init__.py
      ├── app.py
      ├── asgi.py
      ├── cache.py
      ├── config.py
      ├── images.py
      └── store.py

Testing Our Application
-----------------------

So far, so good? We have only tested our application by sending a handful of
requests manually. Have we tested all code paths? Have we covered typical user
inputs to the application?

Creating a comprehensive test suite is vital not only for verifying that the
application is behaving correctly at the moment, but also for limiting the impact
of any regressions introduced into the codebase over time.

In order to implement a test suite, we'll need to revise our dependencies and
decide which abstraction level we are after:

* Will we run a real Redis server?
* Will we store "real" files on a filesystem or just provide a fixture for
  ``aiofiles``?
* Will we inject real dependencies, or use mocks and monkey patching?

There is no right and wrong here, as different testing strategies (or a
combination thereof) have their own advantages in terms of test running time,
how easy it is to implement new tests, how similar the test environment is to
production, etc.

Another thing to choose is a testing framework. Just as in the
:ref:`WSGI tutorial <testing_tutorial>`, let's use
`pytest <http://docs.pytest.org/en/latest/>`_.
This is a matter of taste; if you prefer xUnit/JUnit-style layout, you'll feel
at home with the stdlib's :mod:`unittest`.

In order to more quickly deliver a working solution, we'll allow our tests to access
the real filesystem. For our convenience, ``pytest`` offers several temporary
directory utilities out of the box. Let's wrap its ``tmpdir_factory`` to create
a simple ``storage_path`` fixture that we'll share among all tests in the suite
(in the ``pytest`` parlance, a "session"-scoped fixture).

.. tip::
    The ``pytest`` website includes in-depth documentation on the use of
    fixtures. Please visit `pytest fixtures: explicit, modular, scalable
    <https://docs.pytest.org/en/stable/fixture.html>`__ to learn more.

As mentioned in the :ref:`previous section <asgi_tutorial_caching>`, there are
many ways to spin up a temporary or permanent Redis server; or mock it
altogether. For our tests, we'll try
`fakeredis <https://pypi.org/project/fakeredis/>`__, a pure Python
implementation tailored specifically for writing unit tests.

``pytest`` and ``fakeredis`` can be installed as::

  $ pip install fakeredis pytest

We'll also create a directory for our tests and make it a Python package to avoid
any problems with importing local utility modules or checking code coverage::

  $ mkdir -p tests
  $ touch tests/__init__.py

Next, let's implement fixtures to replace ``uuid`` and ``redis``, and inject them
into our tests via ``conftest.py`` (place your code in the newly created ``tests``
directory):

.. literalinclude:: ../../examples/asgilook/tests/conftest.py
    :language: python

.. note::
    In the ``png_image`` fixture above, we are drawing random images that will
    look different every time the tests are run.

    If your testing flow affords that, it is often a great idea to introduce
    some unpredictability in your test inputs. This will provide more
    confidence that your application can handle a broader range of inputs than
    just 2-3 test cases crafted specifically for that sole purpose.

    On the other hand, random inputs can make assertions less stringent and
    harder to formulate, so judge according to what is the most important for
    your application. You can also try to combine the best of both worlds by
    using a healthy mix of rigid fixtures and fuzz testing.

.. note::
    More information on ``conftest.py``\'s anatomy and ``pytest`` configuration
    can be found in the latter's documentation:
    `conftest.py: local per-directory plugins
    <https://docs.pytest.org/en/stable/writing_plugins.html#localplugin>`__.

With the groundwork in place, we can start with a simple test that will attempt
to GET the ``/images`` resource. Place the following code in a new
``tests/test_images.py`` module:

.. code:: python

    def test_list_images(client):
        resp = client.simulate_get('/images')

        assert resp.status_code == 200
        assert resp.json == []

Let's give it a try::

  $ pytest tests/test_images.py

  ========================= test session starts ==========================
  platform linux -- Python 3.8.0, pytest-6.2.1, py-1.10.0, pluggy-0.13.1
  rootdir: /falcon/tutorials/asgilook
  collected 1 item

  tests/test_images.py .                                           [100%]

  ========================== 1 passed in 0.01s ===========================

Success! 🎉

At this point, our project structure, containing the ``asgilook`` and ``test``
packages, should look like this::

  asgilook
  ├── .venv
  ├── asgilook
  │   ├── __init__.py
  │   ├── app.py
  │   ├── asgi.py
  │   ├── cache.py
  │   ├── config.py
  │   ├── images.py
  │   └── store.py
  └── tests
      ├── __init__.py
      ├── conftest.py
      └── test_images.py

Now, we need more tests! Try adding a few more test cases to ``tests/test_images.py``,
using the :ref:`WSGI Testing Tutorial <testing_tutorial>` as your guide (the
interface for Falcon's testing framework is mostly the same for ASGI vs.
WSGI). Additional examples are available under ``examples/asgilook/tests`` in
the Falcon repository.

.. tip::
    For more advanced test cases, the :class:`falcon.testing.ASGIConductor`
    class is worth a look.

Code Coverage
-------------

How much of our ``asgilook`` code is covered by these tests?

An easy way to get a coverage report is by using the ``pytest-cov`` plugin
(available on PyPi).

After installing ``pytest-cov`` we can generate a coverage report as follows::

  $ pytest --cov=asgilook --cov-report=term-missing tests/

Oh, wow! We do happen to have full line coverage, except for
``asgilook/asgi.py``. If desired, we can instruct ``coverage`` to omit this
module by listing it in the ``omit`` section of a ``.coveragerc`` file.

What is more, we could turn the current coverage into a requirement by
adding ``--cov-fail-under=100`` (or any other percent threshold) to our
``pytest`` command.

.. note::
    The ``pytest-cov`` plugin is quite simplistic; more advanced testing
    strategies such as blending different types of tests and/or running the same
    tests in multiple environments would most probably involve running
    ``coverage`` directly, and combining results.

Debugging ASGI Applications
---------------------------
(This section also applies to WSGI applications)

While developing and testing ASGI applications, understanding how to configure
and utilize logging can be helpful, especially when you encounter unexpected
issues or behaviors.

By default, Falcon does not set up logging for you,
but Python's built-in :mod:`logging` module provides a flexible framework for
emitting and capturing log messages. Here's how you can set up basic logging in
your ASGI Falcon application:

.. code:: python

    import logging

    import falcon


    logging.basicConfig(level=logging.INFO)

    class ErrorResource:
        def on_get(self, req, resp):
            raise Exception('Something went wrong!')

    app = falcon.App()
    app.add_route('/error', ErrorResource())


When the above route is accessed, Falcon will catch the unhandled exception and
automatically log an error message. Below is an example of what the log output
might look like:

.. code-block:: none

    ERROR:falcon.asgi.app:Unhandled exception in ASGI application
    Traceback (most recent call last):
      File "path/to/falcon/app.py", line 123, in __call__
        resp = resource.on_get(req, resp)
      File "/path/to/your/app.py", line 7, in on_get
        raise Exception("Something went wrong!")
    Exception: Something went wrong!


.. note::
   While logging is helpful for development and debugging, be mindful of logging
   sensitive information. Ensure that log files are stored securely and are not
   accessible to unauthorized users.

What Now?
---------

Congratulations, you have successfully completed the Falcon ASGI tutorial!

Needless to say, our sample ASGI application could still be improved in
numerous ways:

* Make the image store persistent and reusable across worker processes.
  Maybe by using a database?
* Improve error handling for malformed images.
* Check how and when Pillow releases the GIL, and tune what is offloaded to a
  threadpool executor.
* Test `Pillow-SIMD <https://pypi.org/project/Pillow-SIMD/>`_ to boost
  performance.
* Publish image upload events via :attr:`SSE <falcon.asgi.Response.sse>` or
  :ref:`WebSockets <ws>`.
* ...And much more (patches welcome, as they say)!

.. tip::
   If you want to add :ref:`WebSocket <ws>` support, please check out our
   :ref:`WebSocket tutorial <tutorial-ws>` too!

Compared to the sync version, asynchronous code can at times be harder to
design and reason about. Should you run into any issues, our friendly community
is available to answer your questions and help you work through any sticky
problems (see also: :ref:`Getting Help <help>`).
