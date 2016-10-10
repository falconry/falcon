Falcon |Docs| |Build Status| |codecov.io|
=========================================

    Perfection is finally attained not when there is no longer anything
    to add, but when there is no longer anything to take away.

    *- Antoine de Saint-Exupéry*

Falcon is a `high-performance Python
framework <http://falconframework.org/index.html>`__ for building cloud
APIs. It encourages the REST architectural style, and tries to do as
little as possible while remaining `highly
effective <http://falconframework.org/index.html#Benefits>`__.

Quick Links
-----------

* `Read the docs <https://falcon.readthedocs.io/en/stable>`__.
* `Join the discussion group <https://groups.google.com/forum/#!forum/falconframework>`__.
* `Hang out in #falconframework on freenode <https://kiwiirc.com/client/irc.freenode.net/?#falconframework>`__.

Design Goals
------------

**Fast.** Cloud APIs need to turn around requests quickly, and make
efficient use of hardware. This is particularly important when serving
many concurrent requests. Falcon is among the fastest WSGI frameworks
available, processing requests
`several times faster <http://falconframework.org/#Metrics>`__ than
other Python web frameworks.

**Light.** Only the essentials are included, with *six* and *mimeparse*
being the only dependencies outside the standard library. We work hard
to keep the code lean, making Falcon easier to test, secure, optimize,
and deploy.

**Flexible.** Falcon is not opinionated when it comes to talking to
databases, rendering content, authorizing requests, etc. You are free to
mix and match your own favorite libraries. Falcon apps work with
any WSGI server, and run great under `CPython 2.6-2.7, PyPy, Jython 2.7,
and CPython 3.3-3.5 <https://travis-ci.org/falconry/falcon>`__.

Features
--------

-  Highly-optimized, extensible code base
-  Intuitive routing via URI templates and REST-inspired resource
   classes
-  Easy access to headers and bodies through request and response
   classes
-  DRY request processing via middleware components and hooks
-  Idiomatic HTTP error responses
-  Straightforward exception handling
-  Snappy unit testing through WSGI helpers and mocks
-  CPython 2.6-2.7, PyPy, Jython 2.7, and CPython 3.3-3.5 support
-  ~20% speed boost when Cython is available

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

You might also like to view our
`Add-on Catalog <https://github.com/falconry/falcon/wiki/Add-on-Catalog>`_,
where you can find a list of add-ons maintained by the community.

Installation
------------

PyPy
^^^^

`PyPy <http://pypy.org/>`__ is the fastest way to run your Falcon app.
However, note that only the PyPy 2.7 compatible release is currently
supported.

.. code:: bash

    $ pip install falcon

CPython
^^^^^^^

Falcon also fully supports
`CPython <https://www.python.org/downloads/>`__ 2.6-3.5.

A universal wheel is available on PyPI for the the Falcon framework.
Installing it is as simple as:

.. code:: bash

    $ pip install falcon

Installing the wheel is a great way to get up and running with Falcon
quickly in a development environment, but for an extra speed boost when
deploying your application in production, Falcon can compile itself with
Cython.

The following commands tell pip to install Cython, and then to invoke
Falcon's ``setup.py``, which will in turn detect the presence of Cython
and then compile (AKA cythonize) the Falcon framework with the system's
default C compiler.

.. code:: bash

    $ pip install cython
    $ pip install --no-binary :all: falcon

**Installing on OS X**

Xcode Command Line Tools are required to compile Cython. Install them
with this command:

.. code:: bash

    $ xcode-select --install

The Clang compiler treats unrecognized command-line options as
errors; this can cause problems under Python 2.6, for example:

.. code:: bash

    clang: error: unknown argument: '-mno-fused-madd' [-Wunused-command-line-argument-hard-error-in-future]

You might also see warnings about unused functions. You can work around
these issues by setting additional Clang C compiler flags as follows:

.. code:: bash

    $ export CFLAGS="-Qunused-arguments -Wno-unused-function"

Dependencies
^^^^^^^^^^^^

Falcon depends on `six` and `python-mimeparse`. `python-mimeparse` is a
better-maintained fork of the similarly named `mimeparse` project.
Normally the correct package will be selected by Falcon's ``setup.py``.
However, if you are using an alternate strategy to manage dependencies,
please take care to install the correct package in order to avoid
errors.

WSGI Server
-----------

Falcon speaks WSGI, and so in order to serve a Falcon app, you will
need a WSGI server. Gunicorn and uWSGI are some of the more popular
ones out there, but anything that can load a WSGI app will do.

.. code:: bash

    $ pip install [gunicorn|uwsgi]

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
    $ pip install -r tools/test-requires
    $ pytest tests

Or, to run the default set of tests:

.. code:: bash

    $ pip install tox && tox

See also the `tox.ini <https://github.com/falconry/falcon/blob/master/tox.ini>`_
file for a full list of available environments.

Read the docs
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

    $ xdg-open docs/_build/html/index.html

Getting started
---------------

Here is a simple, contrived example showing how to create a Falcon-based
API.

.. code:: python

    # things.py

    # Let's get this party started!
    import falcon


    # Falcon follows the REST architectural style, meaning (among
    # other things) that you think in terms of resources and state
    # transitions, which map to HTTP verbs.
    class ThingsResource(object):
        def on_get(self, req, resp):
            """Handles GET requests"""
            resp.status = falcon.HTTP_200  # This is the default status
            resp.body = ('\nTwo things awe me most, the starry sky '
                         'above me and the moral law within me.\n'
                         '\n'
                         '    ~ Immanuel Kant\n\n')

    # falcon.API instances are callable WSGI apps
    app = falcon.API()

    # Resources are represented by long-lived class instances
    things = ThingsResource()

    # things will handle all requests to the '/things' URL path
    app.add_route('/things', things)

You can run the above example using any WSGI server, such as uWSGI or
Gunicorn. For example:

.. code:: bash

    $ pip install gunicorn
    $ gunicorn things:app

Then, in another terminal:

.. code:: bash

    $ curl localhost:8000/things

A more complex example
----------------------

Here is a more involved example that demonstrates reading headers and
query parameters, handling errors, and working with request and response
bodies.

.. code:: python

    import json
    import logging
    import uuid
    from wsgiref import simple_server

    import falcon
    import requests


    class StorageEngine(object):

        def get_things(self, marker, limit):
            return [{'id': str(uuid.uuid4()), 'color': 'green'}]

        def add_thing(self, thing):
            thing['id'] = str(uuid.uuid4())
            return thing


    class StorageError(Exception):

        @staticmethod
        def handle(ex, req, resp, params):
            description = ('Sorry, couldn\'t write your thing to the '
                           'database. It worked on my box.')

            raise falcon.HTTPError(falcon.HTTP_725,
                                   'Database Error',
                                   description)


    class SinkAdapter(object):

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
            resp.body = result.text


    class AuthMiddleware(object):

        def process_request(self, req, resp):
            token = req.get_header('Authorization')
            account_id = req.get_header('Account-ID')

            challenges = ['Token type="Fernet"']

            if token is None:
                description = ('Please provide an auth token '
                               'as part of the request.')

                raise falcon.HTTPUnauthorized('Auth token required',
                                              description,
                                              challenges,
                                              href='http://docs.example.com/auth')

            if not self._token_is_valid(token, account_id):
                description = ('The provided auth token is not valid. '
                               'Please request a new token and try again.')

                raise falcon.HTTPUnauthorized('Authentication required',
                                              description,
                                              challenges,
                                              href='http://docs.example.com/auth')

        def _token_is_valid(self, token, account_id):
            return True  # Suuuuuure it's valid...


    class RequireJSON(object):

        def process_request(self, req, resp):
            if not req.client_accepts_json:
                raise falcon.HTTPNotAcceptable(
                    'This API only supports responses encoded as JSON.',
                    href='http://docs.examples.com/api/json')

            if req.method in ('POST', 'PUT'):
                if 'application/json' not in req.content_type:
                    raise falcon.HTTPUnsupportedMediaType(
                        'This API only supports requests encoded as JSON.',
                        href='http://docs.examples.com/api/json')


    class JSONTranslator(object):

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
                raise falcon.HTTPBadRequest('Empty request body',
                                            'A valid JSON document is required.')

            try:
                req.context['doc'] = json.loads(body.decode('utf-8'))

            except (ValueError, UnicodeDecodeError):
                raise falcon.HTTPError(falcon.HTTP_753,
                                       'Malformed JSON',
                                       'Could not decode the request body. The '
                                       'JSON was incorrect or not encoded as '
                                       'UTF-8.')

        def process_response(self, req, resp, resource):
            if 'result' not in req.context:
                return

            resp.body = json.dumps(req.context['result'])


    def max_body(limit):

        def hook(req, resp, resource, params):
            length = req.content_length
            if length is not None and length > limit:
                msg = ('The size of the request is too large. The body must not '
                       'exceed ' + str(limit) + ' bytes in length.')

                raise falcon.HTTPRequestEntityTooLarge(
                    'Request body is too large', msg)

        return hook


    class ThingsResource(object):

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
                    'Service Outage',
                    description,
                    30)

            # An alternative way of doing DRY serialization would be to
            # create a custom class that inherits from falcon.Request. This
            # class could, for example, have an additional 'doc' property
            # that would serialize to JSON under the covers.
            req.context['result'] = result

            resp.set_header('Powered-By', 'Falcon')
            resp.status = falcon.HTTP_200

        @falcon.before(max_body(64 * 1024))
        def on_post(self, req, resp, user_id):
            try:
                doc = req.context['doc']
            except KeyError:
                raise falcon.HTTPBadRequest(
                    'Missing thing',
                    'A thing must be submitted in the request body.')

            proper_thing = self.db.add_thing(doc)

            resp.status = falcon.HTTP_201
            resp.location = '/%s/things/%s' % (user_id, proper_thing['id'])


    # Configure your WSGI server to load "things.app" (app is a WSGI callable)
    app = falcon.API(middleware=[
        AuthMiddleware(),
        RequireJSON(),
        JSONTranslator(),
    ])

    db = StorageEngine()
    things = ThingsResource(db)
    app.add_route('/{user_id}/things', things)

    # If a responder ever raised an instance of StorageError, pass control to
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


Community
---------

The Falcon community maintains a discussion group that you can use to
share your ideas and ask questions about the framework. To join the
discussion, please visit https://groups.google.com/d/forum/falconframework.

Per our
`Code of Conduct <https://github.com/falconry/falcon/blob/master/CODEOFCONDUCT.md>`_,
we expect everyone who participates in community discussions to act
professionally, and lead by example in encouraging constructive
discussions. Each individual in the community is responsible for
creating a positive, constructive, and productive culture.

We also hang out in
`#falconframework <https://kiwiirc.com/client/irc.freenode.net/?#falconframework>`_
on freenode, where everyone is always welcome to ask questions and share
ideas.

Contributing
------------

Kurt Griffiths (kgriffs) is the creator and current maintainer of the
Falcon framework, with the generous help of a number of stylish and
talented contributors.

Pull requests are always welcome. We use the GitHub issue tracker to
organize our work, put you do not need to open a new issue before
submitting a PR.

Before submitting a pull request, please ensure you have added/updated
the appropriate tests (and that all existing tests still pass with your
changes), and that your coding style follows PEP 8 and doesn't cause
pyflakes to complain.

Commit messages should be formatted using `AngularJS
conventions <http://goo.gl/QpbS7>`__.

Comments follow `Google's style guide <https://google.github.io/styleguide/pyguide.html?showone=Comments#Comments>`__,
with the additional requirement of prefixing inline comments using your
GitHub nick and an appropriate prefix:

- TODO(riker): Damage report!
- NOTE(riker): Well, that's certainly good to know.
- PERF(riker): Travel time to the nearest starbase?
- APPSEC(riker): In all trust, there is the possibility for betrayal.

See also: `CONTRIBUTING.md <https://github.com/falconry/falcon/blob/master/CONTRIBUTING.md>`__

Legal
-----

Copyright 2013-2016 by Rackspace Hosting, Inc. and other contributors as
noted in the individual source files.

Falcon image courtesy of `John
O'Neill <https://commons.wikimedia.org/wiki/File:Brown-Falcon,-Vic,-3.1.2008.jpg>`__.

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
.. |Runner| image:: https://a248.e.akamai.net/assets.github.com/images/icons/emoji/runner.png
    :width: 20
    :height: 20
.. |Build Status| image:: https://travis-ci.org/falconry/falcon.svg
   :target: https://travis-ci.org/falconry/falcon
.. |codecov.io| image:: http://codecov.io/github/falconry/falcon/coverage.svg?branch=master
   :target: http://codecov.io/github/falconry/falcon?branch=master
