.. _tutorial-asgi:

Tutorial (ASGI)
===============

In this tutorial we'll walk through building an API for a simple image sharing
service. Along the way, we'll discuss

.. note::
   This tutorial covers the asynchronous flavor of Falcon using
   the `ASGI <https://asgi.readthedocs.io/en/latest/>`__ protocol.

   Synchronous (`WSGI <https://www.python.org/dev/peps/pep-3333/>`__) Falcon
   application development is covered in our :ref:`WSGI tutorial<tutorial>`.

   New Falcon users may also want to choose the WSGI flavor to familiarize
   themselves with Falcon's basic concepts.

First Steps
-----------

Firstly, let's create a fresh environment and the corresponding project
directory structure, along the lines of :ref:`tutorial-first-steps` from the
WSGI tutorial::

  asgilook
  ├── .venv
  └── asgilook
      ├── __init__.py
      └── app.py

.. note::
   Installing `virtualenv <https://docs.python-guide.org/dev/virtualenvs/>`_ is
   not needed for recent Python 3.x versions. We can simply create a
   *virtualenv* using the ``venv`` module from the standard library,
   for instance::

     $ python3.8 -m venv .venv
     $ source .venv/bin/activate

   However, the above way may be unavailable depending on how Python is
   packaged and installed in your OS. Even if that is the case, installing
   ``virtualenv`` should still work as usual.

   Some of us find it convenient to manage *virtualenv*\s with
   `virtualenvwrapper <https://virtualenvwrapper.readthedocs.io>`_,
   particularly when it comes to hopping between several environments.

At the time of writing, ASGI is not yet available in a stable Falcon release.
We'll need to either install an alpha release::

  $ pip install falcon==3.0.0a2

Or, just check out the latest development version straight from GitHub::

  $ pip install git+https://github.com/falconry/falcon

A :class:`Falcon ASGI application <falcon.asgi.App>` skeleton (``app.py``)
could look like:

.. code:: python

   import falcon.asgi

   app = falcon.asgi.App()

Hosting Our App
---------------

For running our async application, we'll need an
`ASGI <https://asgi.readthedocs.io/>`_ application server. Popular choices
include:

* `Uvicorn <https://www.uvicorn.org/>`_
* `Daphne <https://github.com/django/daphne/>`_
* `Hypercorn <https://pgjones.gitlab.io/hypercorn/>`_

For a simple tutorial application like ours, any of the above should do.
Let's pick the popular ``uvicorn`` for now::

  $ pip install uvicorn

While at it, it might be handy to also install
`HTTPie <https://github.com/jakubroztocil/httpie>`_ HTTP client::

  $ pip install httpie

Now let's try loading our application::

  $ uvicorn asgilook.app:app
  INFO:     Started server process [2020]
  INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
  INFO:     Waiting for application startup.
  INFO:     Application startup complete.

Let's verify it works by trying to access the URL provided above by
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

As in the WSGI "Look" tutorial, we are going to configure at least the storage
location.
There are many approaches to handling application configuration; see also a
related discussion in our FAQ: :ref:`configuration-approaches`

In this tutorial, we'll just pass around a ``Config`` instance to resource
initializers for easier testing (coming later in this tutorial). Create a new
module, ``config.py`` next to ``app.py``, and add the following code to it:

.. code:: python

    import os
    import uuid


    class Config:
        DEFAULT_CONFIG_PATH = '/tmp/asgilook'
        DEFAULT_UUID_GENERATOR = uuid.uuid4

        def __init__(self):
            self.storage_path = (os.environ.get('ASGI_LOOK_STORAGE_PATH')
                                 or self.DEFAULT_CONFIG_PATH)
            if not os.path.exists(self.storage_path):
                os.makedirs(self.storage_path)

            self.uuid_generator = Config.DEFAULT_UUID_GENERATOR

Image Store
-----------

Since we are going to read and write image files, care needs to be taken of
making file I/O non-blocking. We'll give ``aiofiles`` a try::

  pip install aiofiles

In addition, let's twist the original WSGI "Look" design a bit, and convert
all uploaded images to JPEG. Let's try the popular
`Pillow <https://pillow.readthedocs.io/>`_ library for that::

  pip install Pillow

We can now implement a basic async image store as (save the following code as
``store.py`` next to ``app.py`` and ``config.py``):

.. code:: python

    import asyncio
    import datetime
    import io
    import os.path

    import aiofiles
    import falcon
    import PIL.Image


    class Image:

        def __init__(self, config, image_id, size):
            self.config = config
            self.image_id = image_id
            self.size = size
            self.modified = datetime.datetime.utcnow()

        @property
        def path(self):
            return os.path.join(self.config.storage_path, self.image_id)

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
            self.config = config
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

            path = os.path.join(self.config.storage_path, image_id)
            async with aiofiles.open(path, 'wb') as output:
                await output.write(converted)

            stored = Image(self.config, image_id, image.size)
            self._images[image_id] = stored
            return stored

Here we store data using ``aiofiles``, and run ``Pillow`` image transformation
functions in a threadpool executor, hoping that at least some of them release
the GIL during processing.

Images Resource(s)
------------------

In the ASGI flavor of Falcon, all responder methods, hooks and middleware
methods must be awaitable coroutines. With that in mind, let's go on to
implement the image collection, and the individual image resources (the code
below should go into ``images.py``):

.. code:: python

    import aiofiles
    import falcon


    class Images:

        def __init__(self, config, store):
            self.config = config
            self.store = store

        async def on_get(self, req, resp):
            resp.media = [image.serialize() for image in self.store.list_images()]

        async def on_get_image(self, req, resp, image_id):
            image = self.store.get(str(image_id))
            resp.stream = await aiofiles.open(image.path, 'rb')
            resp.content_type = falcon.MEDIA_JPEG

        async def on_post(self, req, resp):
            data = await req.stream.read()
            image_id = str(self.config.uuid_generator())
            image = await self.store.save(image_id, data)

            resp.location = image.uri
            resp.media = image.serialize()
            resp.status = falcon.HTTP_201

Since the first iteration on the ``Images`` class is quite lean, we opted for
implementing two resources, image collection (which supports ``GET`` for
listing the collection, and ``POST`` for uploading a new image) and single
image (which supports ``GET`` for downloading the image), under one class
employing responder name suffixes.

If the application continues to grow in complexity, it might get worth to make
the code cleaner by splitting classes to strictly represent one RESTful
resource per class. See also: :ref:`recommended-route-layout`

.. note::
   Here, we serve the image by simply assigning an open ``aiofiles`` file to
   :attr:`resp.stream <falcon.asgi.Response.stream>`.

.. warning::
   In production deployment, serving files directly from the web server, rather
   than through the Falcon ASGI app, will likely be more efficient, and therefore
   should be preferred. See also: :ref:`faq_static_files`

Running Our Application
-----------------------

Let's refactor our ``app.py`` to allow ``create_app()``\ing whenever we need
it, be it tests or the ASGI application module:

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

But how about route suffixes for the ``Images`` class?
Here, we have to remember to map the single image resource to the
``'/images/{image_id:uuid}.jpeg'`` URI template using the ``'image'``
suffix in the respective :func:`add_route <falcon.asgi.App.add_route>` call.

The ASGI application now resides in ``asgi.py``:

.. Copy-paste under: examples/asgilook/asgilook/asgi.py

.. code:: python

    from .app import create_app

    app = create_app()


Running the application is not too dissimilar from the previous command line::

  $ uvicorn asgilook.asgi:app

Provided ``uvicorn`` is started as per the above command line, let's try
uploading some images::

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

Accessing the newly uploaded image::

  $ http localhost:8000/images/5cfd9fb6-259a-4c72-b8b0-5f4c35edcd3c.jpeg

  HTTP/1.1 200 OK
  content-type: image/jpeg
  date: Tue, 24 Dec 2019 17:34:53 GMT
  server: uvicorn
  transfer-encoding: chunked

  +-----------------------------------------+
  | NOTE: binary data not shown in terminal |
  +-----------------------------------------+

We could also open the link in the web browser to verify the converted JPEG
image looks as intended.

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

The application file layout should now look like::

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

As well as an internal helper to run the ``Pillow`` thumbnail operation that
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
                self.size, self.config.min_thumb_size)]

The updated ``store.py`` should now look like:

.. Copy-paste under: examples/asgilook/asgilook/store.py

.. code:: python

    import asyncio
    import datetime
    import io
    import os.path

    import aiofiles
    import falcon
    import PIL.Image


    class Image:

        def __init__(self, config, image_id, size):
            self.config = config
            self.image_id = image_id
            self.size = size
            self.modified = datetime.datetime.utcnow()

        @property
        def path(self):
            return os.path.join(self.config.storage_path, self.image_id)

        @property
        def uri(self):
            return f'/images/{self.image_id}.jpeg'

        def serialize(self):
            return {
                'id': self.image_id,
                'image': self.uri,
                'modified': falcon.dt_to_http(self.modified),
                'size': self.size,
                'thumbnails': self.thumbnails(),
            }

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
                    self.size, self.config.min_thumb_size)]


    class Store:

        def __init__(self, config):
            self.config = config
            self._images = {}

        def _load_from_bytes(self, data):
            return PIL.Image.open(io.BytesIO(data))

        def _convert(self, image):
            rgb_image = image.convert('RGB')

            converted = io.BytesIO()
            rgb_image.save(converted, 'JPEG')
            return converted.getvalue()

        def _resize(self, data, size):
            image = PIL.Image.open(io.BytesIO(data))
            image.thumbnail(size)

            resized = io.BytesIO()
            image.save(resized, 'JPEG')
            return resized.getvalue()

        def get(self, image_id):
            return self._images.get(image_id)

        def list_images(self):
            return sorted(self._images.values(), key=lambda item: item.modified)

        async def make_thumbnail(self, image, size):
            async with aiofiles.open(image.path, 'rb') as img_file:
                data = await img_file.read()

            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._resize, data, size)

        async def save(self, image_id, data):
            loop = asyncio.get_running_loop()
            image = await loop.run_in_executor(None, self._load_from_bytes, data)
            converted = await loop.run_in_executor(None, self._convert, image)

            path = os.path.join(self.config.storage_path, image_id)
            async with aiofiles.open(path, 'wb') as output:
                await output.write(converted)

            stored = Image(self.config, image_id, image.size)
            self._images[image_id] = stored
            return stored

Let's also add a new ``Thumbnails`` resource to expose the new
functionality. The final version of ``images.py`` reads:

.. Copy-paste under: examples/asgilook/asgilook/images.py

.. code:: python

    import aiofiles
    import falcon


    class Images:

        def __init__(self, config, store):
            self.config = config
            self.store = store

        async def on_get(self, req, resp):
            resp.media = [image.serialize() for image in self.store.list_images()]

        async def on_get_image(self, req, resp, image_id):
            image = self.store.get(str(image_id))
            if not image:
                raise falcon.HTTPNotFound

            resp.stream = await aiofiles.open(image.path, 'rb')
            resp.content_type = falcon.MEDIA_JPEG

        async def on_post(self, req, resp):
            data = await req.stream.read()
            image_id = str(self.config.uuid_generator())
            image = await self.store.save(image_id, data)

            resp.location = image.uri
            resp.media = image.serialize()
            resp.status = falcon.HTTP_201


    class Thumbnails:

        def __init__(self, store):
            self.store = store

        async def on_get(self, req, resp, image_id, width, height):
            image = self.store.get(str(image_id))
            if not image:
                raise falcon.HTTPNotFound
            if req.path not in image.thumbnails():
                raise falcon.HTTPNotFound

            resp.content_type = falcon.MEDIA_JPEG
            resp.data = await self.store.make_thumbnail(image, (width, height))

Adding a new thumbnails route in ``app.py`` is left as an exercise for the
reader (if you get stuck, see the final version of ``app.py`` later in this
tutorial).

The new ``thumbnails`` end-point should now render thumbnails on-the-fly::

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

Let's thus implement response caching in Redis, utilizing
`aioredis <https://github.com/aio-libs/aioredis>`_ for async support::

  pip install aioredis

We will also need to serialize response data (the ``Content-Type`` header and
the body in the first version); ``msgpack`` should do::

  pip install msgpack

Our application will obviously need access to a Redis server. Apart from just
installing Redis server on your machine, one could also:

* Spin up Redis in Docker, eg::

    docker run -p 6379:6379 redis

* Considering Redis is installed on the machine, one could also try
  `pifpaf <https://github.com/jd/pifpaf>`_ for spinning up Redis just
  temporarily for ``uvicorn``::

    pifpaf run redis -- uvicorn asgilook.asgi:app

We are going to perform caching in Falcon :ref:`middleware`. Again, note that
all middleware methods must be asynchronous; even initializing the Redis
connection must be ``await``\ed. How to achieve that in the ``__init__()``
method?

`ASGI application lifespan events
<https://asgi.readthedocs.io/en/latest/specs/lifespan.html>`_ come to the
rescue. An ASGI application server emits these events upon application startup
and shutdown. Let's implement the ``process_startup`` handler in our middleware
to execute code upon our application startup:

.. code:: python

    async def process_startup(self, scope, event):
        self.redis = await self.config.create_redis_pool(
            self.config.redis_host)

.. warning::
    The Lifespan Protocol is an optional extention; please check if your ASGI
    server of choice implements it.

    ``uvicorn`` (that we picked for this tutorial) supports Lifespan.

At minimum, our middleware will need to know the Redis host(s) to connect to.
In addition, we are also going to make our Redis connection factory
configurable in order to afford injecting different Redis client
implementations for production and testing.

Assuming we call our new :ref:`configuration <asgi_tutorial_config>` items
``redis_host`` and ``create_redis_pool()``, respectively, the final version of
``config.py`` now reads:

.. Copy-paste under: examples/asgilook/asgilook/config.py

.. code:: python

    import os
    import uuid

    import aioredis


    class Config:
        DEFAULT_CONFIG_PATH = '/tmp/asgilook'
        DEFAULT_MIN_THUMB_SIZE = 64
        DEFAULT_REDIS_HOST = 'redis://localhost'
        DEFAULT_REDIS_POOL = aioredis.create_redis_pool
        DEFAULT_UUID_GENERATOR = uuid.uuid4

        def __init__(self):
            self.storage_path = (os.environ.get('ASGI_LOOK_STORAGE_PATH')
                                 or self.DEFAULT_CONFIG_PATH)
            if not os.path.exists(self.storage_path):
                os.makedirs(self.storage_path)  # pragma: nocover

            self.create_redis_pool = Config.DEFAULT_REDIS_POOL
            self.min_thumb_size = self.DEFAULT_MIN_THUMB_SIZE
            self.redis_host = self.DEFAULT_REDIS_HOST
            self.uuid_generator = Config.DEFAULT_UUID_GENERATOR

A complete Redis cache component (``cache.py``) could look like:

.. Copy-paste under: examples/asgilook/asgilook/cache.py

.. code:: python

    import msgpack


    class RedisCache:
        PREFIX = 'asgilook:'
        INVALIDATE_ON = frozenset({'DELETE', 'POST', 'PUT'})
        CACHE_HEADER = 'X-ASGILook-Cache'
        TTL = 3600

        def __init__(self, config):
            self.config = config

            # NOTE(vytas): To be initialized upon application startup (see the
            #   method below).
            self.redis = None

        async def process_startup(self, scope, event):
            if self.redis is None:
                self.redis = await self.config.create_redis_pool(
                    self.config.redis_host)

        async def serialize_response(self, resp):
            data = await resp.render_body()
            return msgpack.packb([resp.content_type, data], use_bin_type=True)

        def deserialize_response(self, resp, data):
            resp.content_type, resp.data = msgpack.unpackb(data, raw=False)
            resp.complete = True
            resp.context.cached = True

        async def process_request(self, req, resp):
            resp.context.cached = False

            if req.method in self.INVALIDATE_ON:
                return

            key = f'{self.PREFIX}/{req.path}'
            data = await self.redis.get(key)
            if data is not None:
                self.deserialize_response(resp, data)
                resp.set_header(self.CACHE_HEADER, 'Hit')
            else:
                resp.set_header(self.CACHE_HEADER, 'Miss')

        async def process_response(self, req, resp, resource, req_succeeded):
            if not req_succeeded:
                return

            key = f'{self.PREFIX}/{req.path}'

            if req.method in self.INVALIDATE_ON:
                await self.redis.delete(key)
            elif not resp.context.cached:
                data = await self.serialize_response(resp)
                await self.redis.set(key, data, expire=self.TTL)

For caching to come into effect, we also need to add the ``RedisCache``
component to our application's middleware list.
The final definition of all components in ``app.py`` now is:

.. Copy-paste under: examples/asgilook/asgilook/app.py

.. code:: python

    import falcon.asgi

    from .cache import RedisCache
    from .config import Config
    from .images import Images, Thumbnails
    from .store import Store


    def create_app(config=None):
        config = config or Config()
        cache = RedisCache(config)
        store = Store(config)
        images = Images(config, store)
        thumbnails = Thumbnails(store)

        app = falcon.asgi.App(middleware=[cache])
        app.add_route('/images', images)
        app.add_route('/images/{image_id:uuid}.jpeg', images, suffix='image')
        app.add_route('/thumbnails/{image_id:uuid}/{width:int}x{height:int}.jpeg',
                      thumbnails)

        return app

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

Having a comprehensive test suite is vital not only for verifying that
application is correctly behaving at the moment, but also limiting the impact
of future regressions that will have been introduced into the codebase.

In order to implement actual tests, we'll need to revise our dependencies and
decide which abstraction level we are after:

* Will we run a real Redis server?
* Will we store "real" files on a filesystem or just provide a fixture for
  ``aiofiles``?
* Will we use mocks and monkey patching, or would we inject dependencies?

There is no right and wrong here, as different testing strategies (or a
combination thereof) have their own advantages in terms of test running time,
how easy it is to implement new tests, how close tests are to the "real"
service, and so on.

Another thing to choose is a testing framework. Just as in the
:ref:`WSGI tutorial <testing_tutorial>`, let's use
`pytest <http://docs.pytest.org/en/latest/>`_.
This is a matter of taste; if you prefer xUnit/JUnit-style layout, you'll feel
at home with the stdlib's :mod:`unittest`.

In order to deliver something working faster, we'll allow our tests to access
the real filesystem. As ``pytest`` offers various temporary directory out of
the box, Let's create a simple ``storage_path`` fixture shared among all tests
in the whole suite (in the ``pytest`` parlance, a "session"-scoped fixture).

As mentioned in the :ref:`previous section <asgi_tutorial_caching>`, there are
many ways to spin up a temporary or permanent Redis server; or mock it
altogether. For our tests, we'll try
`fakeredis <https://pypi.org/project/fakeredis/>`__, a pure Python
implementation tailored specifically for writing unit tests.

Let's now write fixtures to replace ``uuid`` and ``aioredis``, and inject them
into our tests via ``conftest.py``:

.. Copy-paste under: examples/asgilook/tests/conftest.py

.. code:: python

    import io
    import random
    import uuid

    import fakeredis.aioredis
    import falcon.asgi
    import falcon.testing
    import PIL.Image
    import PIL.ImageDraw
    import pytest

    from asgilook.app import create_app
    from asgilook.config import Config


    @pytest.fixture()
    def predictable_uuid():
        fixtures = (
            uuid.UUID('36562622-48e5-4a61-be67-e426b11821ed'),
            uuid.UUID('3bc731ac-8cd8-4f39-b6fe-1a195d3b4e74'),
            uuid.UUID('ba1c4951-73bc-45a4-a1f6-aa2b958dafa4'),
        )

        def uuid_func():
            try:
                return next(fixtures_it)
            except StopIteration:
                return uuid.uuid4()

        fixtures_it = iter(fixtures)
        return uuid_func


    @pytest.fixture(scope='session')
    def storage_path(tmpdir_factory):
        return str(tmpdir_factory.mktemp('asgilook'))


    @pytest.fixture
    def client(predictable_uuid, storage_path):
        config = Config()
        config.create_redis_pool = fakeredis.aioredis.create_redis_pool
        config.redis_host = None
        config.storage_path = storage_path
        config.uuid_generator = predictable_uuid

        app = create_app(config)
        return falcon.testing.TestClient(app)


    @pytest.fixture(scope='session')
    def png_image():
        image = PIL.Image.new('RGBA', (640, 360), color='black')

        draw = PIL.ImageDraw.Draw(image)
        for _ in range(32):
            x0 = random.randint(20, 620)
            y0 = random.randint(20, 340)
            x1 = random.randint(20, 620)
            y1 = random.randint(20, 340)
            if x0 > x1:
                x0, x1 = x1, x0
            if y0 > y1:
                y0, y1 = y1, y0
            draw.ellipse([(x0, y0), (x1, y1)], fill='yellow', outline='red')

        output = io.BytesIO()
        image.save(output, 'PNG')
        return output.getvalue()


    @pytest.fixture(scope='session')
    def image_size():
        def report_size(data):
            image = PIL.Image.open(io.BytesIO(data))
            return image.size

        return report_size

.. note::
   In the ``png_image`` fixture above, we are drawing random images that will
   look different every time the tests are run.

   If your testing flow affords that, it is often a great idea to introduce
   some unpredictability in your test inputs. This will provide more confidence
   that your application can handle a broader range of inputs than just 2-3
   test cases crafted specifically for that sole purpose.

   On the other hand, random inputs can make assertions less stringent and
   harder to formulate, so judge according to what is the most important for
   your application. You can also try to combine the best of both worlds by
   using a healthy mix of rigid fixtures and fuzz testing.

With the groundwork in place, we can write a simple test (called
``tests/test_images.py``) that will attempt to simulate access our ``/images``
end-point:

.. code:: python

    def test_list_images(client):
        resp = client.simulate_get('/images')

        assert resp.status_code == 200
        assert resp.json == []

Now, we need more tests!

Feel free to try writing some yourself.
Otherwise, check out ``examples/asgilook/tests`` in the Falcon repository.

Code Coverage
-------------

How much of our ``asgilook`` code is covered by these tests?

An easy way to get a coverage report is using the ``pytest-cov`` plugin
(available on PyPi).

The updated ``pytest`` command line to use this plugin reads::

  $ pytest --cov=asgilook --cov-report=term-missing tests/

Oh, wow! We do happen to have full line coverage (except ``asgilook/asgi.py``
which is meant for the application server).
We can instruct ``coverage`` to omit this file by listing it in the ``omit``
section of a ``.coveragerc`` file.

What is more, we could turn the current coverage into a future requirement by
adding ``--cov-fail-under=100`` (or any other percent threshold) to our
``pytest`` command.

.. note::
   The ``pytest-cov`` plugin is quite simplistic; more advanced testing
   strategies such as blending different type of tests and/or running the same
   tests in multiple environments would most probably involve running
   ``coverage`` directly, and combining results.

What Now?
---------

Congratulations, you have successfully completed the Falcon ASGI tutorial!

Needless to say, our first Falcon+ASGI application could still be improved in
numerous ways:

* Make image store persistent and reusable across worker processes.
  Maybe by using a database?
* Improve error handling for malformed images.
* Check how and when Pillow releases the GIL, and tune what is offloaded to a
  threadpool executor.
* Test `Pillow-SIMD <https://pypi.org/project/Pillow-SIMD/>`_ to boost
  performance.
* Publish image upload events via :attr:`SSE <falcon.asgi.Response.sse>` or
  WebSockets.
* ...And much more (patches welcome, as they say)!

Compared to the sync version, asynchronous code can at times be harder to
design and reason about. Should you run into any issues, our friendly community
is available to answer your questions and help you work through these sticky
problems.
See also: :ref:`Getting Help <help>`.
