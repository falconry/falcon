.. raw:: html

    <a href="https://falconframework.org" target="_blank">
    <img
        src="https://raw.githubusercontent.com/falconry/falcon/master/logo/banner.jpg"
        alt="Falcon web framework logo"
        style="width:100%"
    >
    </a>

|Build Status| |Docs| |codecov.io| |Blue|

The Falcon Web Framework
========================

`Falcon <https://falconframework.org>`__ is a minimalist ASGI/WSGI framework for
building mission-critical REST APIs and microservices, with a focus on
reliability, correctness, and performance at scale.

When it comes to building HTTP APIs, other frameworks weigh you down with tons
of dependencies and unnecessary abstractions. Falcon cuts to the chase with a
clean design that embraces HTTP and the REST architectural style.

Falcon apps work with any `WSGI <https://www.python.org/dev/peps/pep-3333/>`_
or `ASGI <https://asgi.readthedocs.io/en/latest/>`_ server, and run like a
champ under CPython 3.5+ and PyPy 3.5+ (3.6+ required for ASGI).

Quick Links
-----------

* `Read the docs <https://falcon.readthedocs.io/en/stable>`_
  (`FAQ <https://falcon.readthedocs.io/en/stable/user/faq.html>`_ -
  `getting help <https://falcon.readthedocs.io/en/stable/community/help.html>`_ -
  `reference <https://falcon.readthedocs.io/en/stable/api/index.html>`_)
* `Falcon add-ons and complementary packages <https://github.com/falconry/falcon/wiki>`_
* `Falcon articles, talks and podcasts <https://github.com/falconry/falcon/wiki/Articles,-Talks-and-Podcasts>`_
* `falconry/user for Falcon users <https://gitter.im/falconry/user>`_ @ Gitter
* `falconry/dev for Falcon contributors <https://gitter.im/falconry/dev>`_ @ Gitter

What People are Saying
----------------------

"Falcon is rock solid and it's fast."

"We have been using Falcon as a replacement for [another framework] and
we simply love the performance (three times faster) and code base size (easily
half of our [original] code)."

"I'm loving #falconframework! Super clean and simple, I finally
have the speed and flexibility I need!"

"Falcon looks great so far. I hacked together a quick test for a
tiny server of mine and was ~40% faster with only 20 minutes of
work."

"I feel like I'm just talking HTTP at last, with nothing in the
middle. Falcon seems like the requests of backend."

"The source code for Falcon is so good, I almost prefer it to
documentation. It basically can't be wrong."

"What other framework has integrated support for 786 TRY IT NOW ?"

Features
--------

Falcon tries to do as little as possible while remaining highly effective.

- ASGI, WSGI, and WebSocket support
- Native ``asyncio`` support
- No reliance on magic globals for routing and state management
- Stable interfaces with an emphasis on backwards-compatibility
- Simple API modeling through centralized RESTful routing
- Highly-optimized, extensible code base
- Easy access to headers and bodies through request and response
  classes
- DRY request processing via middleware components and hooks
- Strict adherence to RFCs
- Idiomatic HTTP error responses
- Straightforward exception handling
- Snappy testing with WSGI/ASGI helpers and mocks
- CPython 3.5+ and PyPy 3.5+ support

.. Patron list starts here. For Python package, we substitute this section with:
   Support Falcon Development
   --------------------------

A Big Thank You to Our Patrons!
-------------------------------

.. raw:: html

    <p>
    <a href="https://www.govcert.lu/" target="_blank"><img src="https://falconframework.org/assets/govcert.png" height="60" alt="CERT Gouvernemental Luxembourg" ></a>
     </p>

    <p>
        <a href="https://www.kontrolnaya-rabota.ru/s/" target="_blank"><img src="https://falconframework.org/assets/rabota.jpg" height="30" alt="Examination RU" style="margin-right: 10px"></a>

        <a href="https://www.pnk.sh/python-falcon" target="_blank"><img src="https://falconframework.org/assets/paris.svg" height="30" alt="Paris Kejser" style="margin-right: 10px"></a>

        <a href="https://www.algolia.com" target="_blank" style="margin-right: 10px"><img src="https://falconframework.org/assets/algolia.svg" height="30" alt="Algolia"></a>

        <a href="https://www.salesforce.com" target="_blank"><img src="https://falconframework.org/assets/salesforce.svg" height="30" alt="Salesforce"></a>
    </p>

    <p>
        <a href="https://www.misaka.io" target="_blank" style="margin-right: 10px"><img src="https://falconframework.org/assets/misaka.svg" height="30" alt="Misaka Network"></a>
        <a href="https://github.com/LikaloLLC" target="_blank" style="margin-right: 10px"><img src="https://falconframework.org/assets/likalo.png" height="30" alt="Likalo"></a>
    </p>

.. Patron list ends here (see the comment above this section).

Has Falcon helped you make an awesome app? Show your support today with a one-time donation or by becoming a patron. Supporters get cool gear, an opportunity to promote their brand to Python developers, and
prioritized support.

* `Learn how to support Falcon development <https://falconframework.org/#sectionSupportFalconDevelopment>`_

Thanks!

How is Falcon Different?
------------------------

    Perfection is finally attained not when there is no longer anything
    to add, but when there is no longer anything to take away.

    *- Antoine de Saint-Exupéry*

We designed Falcon to support the demanding needs of large-scale
microservices and responsive app backends. Falcon complements more
general Python web frameworks by providing bare-metal performance,
reliability, and flexibility wherever you need it.

**Reliable.** We go to great lengths to avoid introducing breaking changes, and
when we do they are fully documented and only introduced (in the spirit of
`SemVer <http://semver.org/>`_) with a major version increment. The code is
rigorously tested with numerous inputs and we require 100% coverage at all
times. Falcon has no dependencies outside the standard library, helping
minimize your app's attack surface while avoiding transitive bugs and breaking
changes.

**Debuggable.** Falcon eschews magic. It's easy to tell which inputs lead to
which outputs. Unhandled exceptions are never encapsulated or masked.
Potentially surprising behaviors, such as automatic request body parsing, are
well-documented and disabled by default. Finally, when it comes to the
framework itself, we take care to keep logic paths simple and understandable.
All this makes it easier to reason about the code and to debug edge cases in
large-scale deployments.

**Fast.** Same hardware, more requests. Falcon turns around requests
significantly faster than other popular Python frameworks like Django and
Flask. For an extra speed boost, Falcon compiles itself with Cython when
available, and also works well with `PyPy <https://pypy.org>`_. Considering a
move to another programming language? Benchmark with Falcon+PyPy first!

**Flexible.** Falcon leaves a lot of decisions and implementation details to
you, the API developer. This gives you a lot of freedom to customize and tune
your implementation. It also helps you understand your apps at a deeper level,
making them easier to tune, debug, and refactor over the long run. Falcon's
minimalist design provides space for Python community members to independently
innovate on `Falcon add-ons and complementary packages
<https://github.com/falconry/falcon/wiki>`_.

Who's Using Falcon?
-------------------

Falcon is used around the world by a growing number of organizations,
including:

- 7ideas
- Cronitor
- EMC
- Hurricane Electric
- Leadpages
- OpenStack
- Rackspace
- Shiftgig
- tempfil.es
- Opera Software

If you are using the Falcon framework for a community or commercial
project, please consider adding your information to our wiki under
`Who's Using Falcon? <https://github.com/falconry/falcon/wiki/Who's-using-Falcon%3F>`_

Community
---------

A number of Falcon add-ons, templates, and complementary packages are
available for use in your projects. We've listed several of these on the
`Falcon wiki <https://github.com/falconry/falcon/wiki>`_ as a starting
point, but you may also wish to search PyPI for additional resources.

The Falconry community on Gitter is a great place to ask questions and
share your ideas. You can find us in `falconry/user
<https://gitter.im/falconry/user>`_. We also have a
`falconry/dev <https://gitter.im/falconry/dev>`_ room for discussing
the design and development of the framework itself.

Per our
`Code of Conduct <https://github.com/falconry/falcon/blob/master/CODEOFCONDUCT.md>`_,
we expect everyone who participates in community discussions to act
professionally, and lead by example in encouraging constructive
discussions. Each individual in the community is responsible for
creating a positive, constructive, and productive culture.

Installation
------------

PyPy
^^^^

`PyPy <http://pypy.org/>`__ is the fastest way to run your Falcon app.
PyPy3.5+ is supported as of PyPy v5.10.

.. code:: bash

    $ pip install falcon

Or, to install the latest beta or release candidate, if any:

.. code:: bash

    $ pip install --pre falcon

CPython
^^^^^^^

Falcon also fully supports
`CPython <https://www.python.org/downloads/>`__ 3.5+.

The latest stable version of Falcon can be installed directly from PyPI:

.. code:: bash

    $ pip install falcon

Or, to install the latest beta or release candidate, if any:

.. code:: bash

    $ pip install --pre falcon

In order to provide an extra speed boost, Falcon can compile itself with
Cython. Wheels containing pre-compiled binaries are available from PyPI for
several common platforms. However, if a wheel for your platform of choice is not
available, you can install the source distribution. The installation process
will automatically try to cythonize Falcon for your environment, falling back to
a normal pure-Python install if any issues are encountered during the
cythonization step:

.. code:: bash

    $ pip install --no-binary :all: falcon

If you want to verify that Cython is being invoked, simply
pass the verbose flag `-v` to pip in order to echo the compilation commands.

The cythonization step is only active when using the ``CPython`` Python
implementation, so installing using ``PyPy`` will skip it.
If you want to skip Cython compilation step and install
the pure-Python version directly you can set the environment variable
``FALCON_DISABLE_CYTHON`` to a non empty value before install:

.. code:: bash

    $ FALCON_DISABLE_CYTHON=Y pip install -v --no-binary :all: falcon

Please note that ``pip>=10`` is required to be able to install Falcon from
source.

**Installing on OS X**

Xcode Command Line Tools are required to compile Cython. Install them
with this command:

.. code:: bash

    $ xcode-select --install

The Clang compiler treats unrecognized command-line options as
errors, for example:

.. code:: bash

    clang: error: unknown argument: '-mno-fused-madd' [-Wunused-command-line-argument-hard-error-in-future]

You might also see warnings about unused functions. You can work around
these issues by setting additional Clang C compiler flags as follows:

.. code:: bash

    $ export CFLAGS="-Qunused-arguments -Wno-unused-function"

Dependencies
^^^^^^^^^^^^

Falcon does not require the installation of any other packages, although if
Cython has been installed into the environment, it will be used to optimize
the framework as explained above.

WSGI Server
-----------

Falcon speaks `WSGI <https://www.python.org/dev/peps/pep-3333/>`_ (or
`ASGI <https://asgi.readthedocs.io/en/latest/>`_; see also below). In order to
serve a Falcon app, you will need a WSGI server. Gunicorn and uWSGI are some of
the more popular ones out there, but anything that can load a WSGI app will do.

.. code:: bash

    $ pip install [gunicorn|uwsgi]

ASGI Server
-----------

In order to serve a Falcon ASGI app, you will need an ASGI server. Uvicorn
is a popular choice:

.. code:: bash

    $ pip install uvicorn

Source Code
-----------

Falcon `lives on GitHub <https://github.com/falconry/falcon>`_, making the
code easy to browse, download, fork, etc. Pull requests are always welcome! Also,
please remember to star the project if it makes you happy. :)

Once you have cloned the repo or downloaded a tarball from GitHub, you
can install Falcon like this:

.. code:: bash

    $ cd falcon
    $ pip install .

Or, if you want to edit the code, first fork the main repo, clone the fork
to your desktop, and then run the following to install it using symbolic
linking, so that when you change your code, the changes will be automagically
available to your app without having to reinstall the package:

.. code:: bash

    $ cd falcon
    $ pip install -e .

You can manually test changes to the Falcon framework by switching to the
directory of the cloned repo and then running pytest:

.. code:: bash

    $ cd falcon
    $ pip install -r requirements/tests
    $ pytest tests

Or, to run the default set of tests:

.. code:: bash

    $ pip install tox && tox

See also the `tox.ini <https://github.com/falconry/falcon/blob/master/tox.ini>`_
file for a full list of available environments.

Read the Docs
-------------

The docstrings in the Falcon code base are quite extensive, and we
recommend keeping a REPL running while learning the framework so that
you can query the various modules and classes as you have questions.

Online docs are available at: https://falcon.readthedocs.io

You can build the same docs locally as follows:

.. code:: bash

    $ pip install tox && tox -e docs

Once the docs have been built, you can view them by opening the following
index page in your browser. On OS X it's as simple as::

    $ open docs/_build/html/index.html

Or on Linux:

.. code:: bash

    $ xdg-open docs/_build/html/index.html

Getting Started
---------------

Here is a simple, contrived example showing how to create a Falcon-based
WSGI app (the ASGI version is included further down):

.. code:: python

    # examples/things.py

    # Let's get this party started!
    from wsgiref.simple_server import make_server

    import falcon


    # Falcon follows the REST architectural style, meaning (among
    # other things) that you think in terms of resources and state
    # transitions, which map to HTTP verbs.
    class ThingsResource:
        def on_get(self, req, resp):
            """Handles GET requests"""
            resp.status = falcon.HTTP_200  # This is the default status
            resp.content_type = falcon.MEDIA_TEXT  # Default is JSON, so override
            resp.text = ('\nTwo things awe me most, the starry sky '
                         'above me and the moral law within me.\n'
                         '\n'
                         '    ~ Immanuel Kant\n\n')


    # falcon.App instances are callable WSGI apps...
    # in larger applications the app is created in a separate file
    app = falcon.App()

    # Resources are represented by long-lived class instances
    things = ThingsResource()

    # things will handle all requests to the '/things' URL path
    app.add_route('/things', things)

    if __name__ == '__main__':
        with make_server('', 8000, app) as httpd:
            print('Serving on port 8000...')

            # Serve until process is killed
            httpd.serve_forever()

You can run the above example directly using the included wsgiref server:

.. code:: bash

    $ pip install falcon
    $ python things.py

Then, in another terminal:

.. code:: bash

    $ curl localhost:8000/things

The ASGI version of the example is similar:

.. code:: python

    # examples/things_asgi.py

    import falcon
    import falcon.asgi


    # Falcon follows the REST architectural style, meaning (among
    # other things) that you think in terms of resources and state
    # transitions, which map to HTTP verbs.
    class ThingsResource:
        async def on_get(self, req, resp):
            """Handles GET requests"""
            resp.status = falcon.HTTP_200  # This is the default status
            resp.content_type = falcon.MEDIA_TEXT  # Default is JSON, so override
            resp.text = ('\nTwo things awe me most, the starry sky '
                         'above me and the moral law within me.\n'
                         '\n'
                         '    ~ Immanuel Kant\n\n')


    # falcon.asgi.App instances are callable ASGI apps...
    # in larger applications the app is created in a separate file
    app = falcon.asgi.App()

    # Resources are represented by long-lived class instances
    things = ThingsResource()

    # things will handle all requests to the '/things' URL path
    app.add_route('/things', things)

You can run the ASGI version with uvicorn or any other ASGI server:

.. code:: bash

    $ pip install falcon uvicorn
    $ uvicorn things_asgi:app

A More Complex Example (WSGI)
-----------------------------

Here is a more involved example that demonstrates reading headers and query
parameters, handling errors, and working with request and response bodies.
Note that this example assumes that the
`requests <https://pypi.org/project/requests/>`_ package has been installed.

(For the equivalent ASGI app, see: `A More Complex Example (ASGI)`_).

.. code:: python

    # examples/things_advanced.py

    import json
    import logging
    import uuid
    from wsgiref import simple_server

    import falcon
    import requests


    class StorageEngine:

        def get_things(self, marker, limit):
            return [{'id': str(uuid.uuid4()), 'color': 'green'}]

        def add_thing(self, thing):
            thing['id'] = str(uuid.uuid4())
            return thing


    class StorageError(Exception):

        @staticmethod
        def handle(ex, req, resp, params):
            # TODO: Log the error, clean up, etc. before raising
            raise falcon.HTTPInternalServerError()


    class SinkAdapter:

        engines = {
            'ddg': 'https://duckduckgo.com',
            'y': 'https://search.yahoo.com/search',
        }

        def __call__(self, req, resp, engine):
            url = self.engines[engine]
            params = {'q': req.get_param('q', True)}
            result = requests.get(url, params=params)

            resp.status = str(result.status_code) + ' ' + result.reason
            resp.content_type = result.headers['content-type']
            resp.text = result.text


    class AuthMiddleware:

        def process_request(self, req, resp):
            token = req.get_header('Authorization')
            account_id = req.get_header('Account-ID')

            challenges = ['Token type="Fernet"']

            if token is None:
                description = ('Please provide an auth token '
                               'as part of the request.')

                raise falcon.HTTPUnauthorized(title='Auth token required',
                                              description=description,
                                              challenges=challenges,
                                              href='http://docs.example.com/auth')

            if not self._token_is_valid(token, account_id):
                description = ('The provided auth token is not valid. '
                               'Please request a new token and try again.')

                raise falcon.HTTPUnauthorized(title='Authentication required',
                                              description=description,
                                              challenges=challenges,
                                              href='http://docs.example.com/auth')

        def _token_is_valid(self, token, account_id):
            return True  # Suuuuuure it's valid...


    class RequireJSON:

        def process_request(self, req, resp):
            if not req.client_accepts_json:
                raise falcon.HTTPNotAcceptable(
                    description='This API only supports responses encoded as JSON.',
                    href='http://docs.examples.com/api/json')

            if req.method in ('POST', 'PUT'):
                if 'application/json' not in req.content_type:
                    raise falcon.HTTPUnsupportedMediaType(
                        title='This API only supports requests encoded as JSON.',
                        href='http://docs.examples.com/api/json')


    class JSONTranslator:
        # NOTE: Normally you would simply use req.media and resp.media for
        # this particular use case; this example serves only to illustrate
        # what is possible.

        def process_request(self, req, resp):
            # req.stream corresponds to the WSGI wsgi.input environ variable,
            # and allows you to read bytes from the request body.
            #
            # See also: PEP 3333
            if req.content_length in (None, 0):
                # Nothing to do
                return

            body = req.stream.read()
            if not body:
                raise falcon.HTTPBadRequest(title='Empty request body',
                                            description='A valid JSON document is required.')

            try:
                req.context.doc = json.loads(body.decode('utf-8'))

            except (ValueError, UnicodeDecodeError):
                description = ('Could not decode the request body. The '
                               'JSON was incorrect or not encoded as '
                               'UTF-8.')

                raise falcon.HTTPBadRequest(title='Malformed JSON',
                                            description=description)

        def process_response(self, req, resp, resource, req_succeeded):
            if not hasattr(resp.context, 'result'):
                return

            resp.text = json.dumps(resp.context.result)


    def max_body(limit):

        def hook(req, resp, resource, params):
            length = req.content_length
            if length is not None and length > limit:
                msg = ('The size of the request is too large. The body must not '
                       'exceed ' + str(limit) + ' bytes in length.')

                raise falcon.HTTPPayloadTooLarge(
                    title='Request body is too large', description=msg)

        return hook


    class ThingsResource:

        def __init__(self, db):
            self.db = db
            self.logger = logging.getLogger('thingsapp.' + __name__)

        def on_get(self, req, resp, user_id):
            marker = req.get_param('marker') or ''
            limit = req.get_param_as_int('limit') or 50

            try:
                result = self.db.get_things(marker, limit)
            except Exception as ex:
                self.logger.error(ex)

                description = ('Aliens have attacked our base! We will '
                               'be back as soon as we fight them off. '
                               'We appreciate your patience.')

                raise falcon.HTTPServiceUnavailable(
                    title='Service Outage',
                    description=description,
                    retry_after=30)

            # NOTE: Normally you would use resp.media for this sort of thing;
            # this example serves only to demonstrate how the context can be
            # used to pass arbitrary values between middleware components,
            # hooks, and resources.
            resp.context.result = result

            resp.set_header('Powered-By', 'Falcon')
            resp.status = falcon.HTTP_200

        @falcon.before(max_body(64 * 1024))
        def on_post(self, req, resp, user_id):
            try:
                doc = req.context.doc
            except AttributeError:
                raise falcon.HTTPBadRequest(
                    title='Missing thing',
                    description='A thing must be submitted in the request body.')

            proper_thing = self.db.add_thing(doc)

            resp.status = falcon.HTTP_201
            resp.location = '/%s/things/%s' % (user_id, proper_thing['id'])

    # Configure your WSGI server to load "things.app" (app is a WSGI callable)
    app = falcon.App(middleware=[
        AuthMiddleware(),
        RequireJSON(),
        JSONTranslator(),
    ])

    db = StorageEngine()
    things = ThingsResource(db)
    app.add_route('/{user_id}/things', things)

    # If a responder ever raises an instance of StorageError, pass control to
    # the given handler.
    app.add_error_handler(StorageError, StorageError.handle)

    # Proxy some things to another service; this example shows how you might
    # send parts of an API off to a legacy system that hasn't been upgraded
    # yet, or perhaps is a single cluster that all data centers have to share.
    sink = SinkAdapter()
    app.add_sink(sink, r'/search/(?P<engine>ddg|y)\Z')

    # Useful for debugging problems in your API; works with pdb.set_trace(). You
    # can also use Gunicorn to host your app. Gunicorn can be configured to
    # auto-restart workers when it detects a code change, and it also works
    # with pdb.
    if __name__ == '__main__':
        httpd = simple_server.make_server('127.0.0.1', 8000, app)
        httpd.serve_forever()

Again this code uses wsgiref, but you can also run the above example using
any WSGI server, such as uWSGI or Gunicorn. For example:

.. code:: bash

    $ pip install requests gunicorn
    $ gunicorn things:app

On Windows you can run Gunicorn and uWSGI via WSL, or you might try Waitress:

.. code:: bash

    $ pip install requests waitress
    $ waitress-serve --port=8000 things:app

To test this example, open another terminal and run:

.. code:: bash

    $ http localhost:8000/1/things authorization:custom-token

You can also view the application configuration from the CLI via the
``falcon-inspect-app`` script that is bundled with the framework:

.. code:: bash

    falcon-inspect-app things_advanced:app

A More Complex Example (ASGI)
-----------------------------

Here's the ASGI version of the app from above. Note that it uses the
`httpx <https://pypi.org/project/httpx/>`_ package in lieu of
`requests <https://pypi.org/project/requests/>`_.

.. code:: python

    # examples/things_advanced_asgi.py

    import json
    import logging
    import uuid

    import falcon
    import falcon.asgi
    import httpx


    class StorageEngine:

        async def get_things(self, marker, limit):
            return [{'id': str(uuid.uuid4()), 'color': 'green'}]

        async def add_thing(self, thing):
            thing['id'] = str(uuid.uuid4())
            return thing


    class StorageError(Exception):

        @staticmethod
        async def handle(ex, req, resp, params):
            # TODO: Log the error, clean up, etc. before raising
            raise falcon.HTTPInternalServerError()


    class SinkAdapter:

        engines = {
            'ddg': 'https://duckduckgo.com',
            'y': 'https://search.yahoo.com/search',
        }

        async def __call__(self, req, resp, engine):
            url = self.engines[engine]
            params = {'q': req.get_param('q', True)}

            async with httpx.AsyncClient() as client:
                result = await client.get(url, params=params)

            resp.status = result.status_code
            resp.content_type = result.headers['content-type']
            resp.text = result.text


    class AuthMiddleware:

        async def process_request(self, req, resp):
            token = req.get_header('Authorization')
            account_id = req.get_header('Account-ID')

            challenges = ['Token type="Fernet"']

            if token is None:
                description = ('Please provide an auth token '
                               'as part of the request.')

                raise falcon.HTTPUnauthorized(title='Auth token required',
                                              description=description,
                                              challenges=challenges,
                                              href='http://docs.example.com/auth')

            if not self._token_is_valid(token, account_id):
                description = ('The provided auth token is not valid. '
                               'Please request a new token and try again.')

                raise falcon.HTTPUnauthorized(title='Authentication required',
                                              description=description,
                                              challenges=challenges,
                                              href='http://docs.example.com/auth')

        def _token_is_valid(self, token, account_id):
            return True  # Suuuuuure it's valid...


    class RequireJSON:

        async def process_request(self, req, resp):
            if not req.client_accepts_json:
                raise falcon.HTTPNotAcceptable(
                    description='This API only supports responses encoded as JSON.',
                    href='http://docs.examples.com/api/json')

            if req.method in ('POST', 'PUT'):
                if 'application/json' not in req.content_type:
                    raise falcon.HTTPUnsupportedMediaType(
                        description='This API only supports requests encoded as JSON.',
                        href='http://docs.examples.com/api/json')


    class JSONTranslator:
        # NOTE: Normally you would simply use req.get_media() and resp.media for
        # this particular use case; this example serves only to illustrate
        # what is possible.

        async def process_request(self, req, resp):
            # NOTE: Test explicitly for 0, since this property could be None in
            # the case that the Content-Length header is missing (in which case we
            # can't know if there is a body without actually attempting to read
            # it from the request stream.)
            if req.content_length == 0:
                # Nothing to do
                return

            body = await req.stream.read()
            if not body:
                raise falcon.HTTPBadRequest(title='Empty request body',
                                            description='A valid JSON document is required.')

            try:
                req.context.doc = json.loads(body.decode('utf-8'))

            except (ValueError, UnicodeDecodeError):
                description = ('Could not decode the request body. The '
                               'JSON was incorrect or not encoded as '
                               'UTF-8.')

                raise falcon.HTTPBadRequest(title='Malformed JSON',
                                            description=description)

        async def process_response(self, req, resp, resource, req_succeeded):
            if not hasattr(resp.context, 'result'):
                return

            resp.text = json.dumps(resp.context.result)


    def max_body(limit):

        async def hook(req, resp, resource, params):
            length = req.content_length
            if length is not None and length > limit:
                msg = ('The size of the request is too large. The body must not '
                       'exceed ' + str(limit) + ' bytes in length.')

                raise falcon.HTTPPayloadTooLarge(
                    title='Request body is too large', description=msg)

        return hook


    class ThingsResource:

        def __init__(self, db):
            self.db = db
            self.logger = logging.getLogger('thingsapp.' + __name__)

        async def on_get(self, req, resp, user_id):
            marker = req.get_param('marker') or ''
            limit = req.get_param_as_int('limit') or 50

            try:
                result = await self.db.get_things(marker, limit)
            except Exception as ex:
                self.logger.error(ex)

                description = ('Aliens have attacked our base! We will '
                               'be back as soon as we fight them off. '
                               'We appreciate your patience.')

                raise falcon.HTTPServiceUnavailable(
                    title='Service Outage',
                    description=description,
                    retry_after=30)

            # NOTE: Normally you would use resp.media for this sort of thing;
            # this example serves only to demonstrate how the context can be
            # used to pass arbitrary values between middleware components,
            # hooks, and resources.
            resp.context.result = result

            resp.set_header('Powered-By', 'Falcon')
            resp.status = falcon.HTTP_200

        @falcon.before(max_body(64 * 1024))
        async def on_post(self, req, resp, user_id):
            try:
                doc = req.context.doc
            except AttributeError:
                raise falcon.HTTPBadRequest(
                    title='Missing thing',
                    description='A thing must be submitted in the request body.')

            proper_thing = await self.db.add_thing(doc)

            resp.status = falcon.HTTP_201
            resp.location = '/%s/things/%s' % (user_id, proper_thing['id'])


    # The app instance is an ASGI callable
    app = falcon.asgi.App(middleware=[
        # AuthMiddleware(),
        RequireJSON(),
        JSONTranslator(),
    ])

    db = StorageEngine()
    things = ThingsResource(db)
    app.add_route('/{user_id}/things', things)

    # If a responder ever raises an instance of StorageError, pass control to
    # the given handler.
    app.add_error_handler(StorageError, StorageError.handle)

    # Proxy some things to another service; this example shows how you might
    # send parts of an API off to a legacy system that hasn't been upgraded
    # yet, or perhaps is a single cluster that all data centers have to share.
    sink = SinkAdapter()
    app.add_sink(sink, r'/search/(?P<engine>ddg|y)\Z')

You can run the ASGI version with any ASGI server, such as uvicorn:

.. code:: bash

    $ pip install falcon httpx uvicorn
    $ uvicorn things_advanced_asgi:app

Contributing
------------

Thanks for your interest in the project! We welcome pull requests from
developers of all skill levels. To get started, simply fork the master branch
on GitHub to your personal account and then clone the fork into your
development environment.

If you would like to contribute but don't already have something in mind,
we invite you to take a look at the issues listed under our
`next milestone <https://github.com/falconry/falcon/milestones>`_.
If you see one you'd like to work on, please leave a quick comment so that we don't
end up with duplicated effort. Thanks in advance!

Please note that all contributors and maintainers of this project are subject to our `Code of Conduct <https://github.com/falconry/falcon/blob/master/CODEOFCONDUCT.md>`_.

Before submitting a pull request, please ensure you have added/updated
the appropriate tests (and that all existing tests still pass with your
changes), and that your coding style follows PEP 8 and doesn't cause
pyflakes to complain.

Commit messages should be formatted using `AngularJS
conventions <https://github.com/angular/angular.js/blob/master/DEVELOPERS.md#-git-commit-guidelines>`__.

Comments follow `Google's style guide <https://google.github.io/styleguide/pyguide.html?showone=Comments#Comments>`__,
with the additional requirement of prefixing inline comments using your
GitHub nick and an appropriate prefix:

- TODO(riker): Damage report!
- NOTE(riker): Well, that's certainly good to know.
- PERF(riker): Travel time to the nearest starbase?
- APPSEC(riker): In all trust, there is the possibility for betrayal.

The core Falcon project maintainers are:

- Kurt Griffiths, Project Lead (**kgriffs** on GH, Gitter, and Twitter)
- John Vrbanac (**jmvrbanac** on GH, Gitter, and Twitter)
- Vytautas Liuolia (**vytas7** on GH and Gitter, and **vliuolia** on Twitter)
- Nick Zaccardi (**nZac** on GH and Gitter)
- Federico Caselli (**CaselIT** on GH and Gitter)

Please don't hesitate to reach out if you have any questions, or just need a
little help getting started. You can find us in
`falconry/dev <https://gitter.im/falconry/dev>`_ on Gitter.

See also: `CONTRIBUTING.md <https://github.com/falconry/falcon/blob/master/CONTRIBUTING.md>`__

Legal
-----

Copyright 2013-2023 by Individual and corporate contributors as
noted in the individual source files.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use any portion of the Falcon framework except in compliance with
the License. Contributors agree to license their work under the same
License. You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

.. |Docs| image:: https://readthedocs.org/projects/falcon/badge/?version=stable
    :target: https://falcon.readthedocs.io/en/stable/?badge=stable
    :alt: Falcon web framework docs
.. |Build Status| image:: https://github.com/falconry/falcon/workflows/Run%20tests/badge.svg
   :target: https://github.com/falconry/falcon/actions?query=workflow%3A%22Run+tests%22
.. |codecov.io| image:: https://codecov.io/gh/falconry/falcon/branch/master/graphs/badge.svg
   :target: http://codecov.io/gh/falconry/falcon
.. |Blue| image:: https://img.shields.io/badge/code%20style-blue-blue.svg
    :target: https://blue.readthedocs.io/
    :alt: code style: blue
