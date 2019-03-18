.. raw:: html

    <a href="https://falconframework.org" target="_blank">
    <img
        src="https://raw.githubusercontent.com/falconry/falcon/master/logo/banner.jpg"
        alt="Falcon web framework logo"
        style="width:100%"
    >
    </a>

|Docs| |Build Status| |codecov.io|

The Falcon Web Framework
========================

`Falcon <https://falconframework.org>`__ is a reliable,
high-performance Python web framework for building
large-scale app backends and microservices. It encourages the REST
architectural style, and tries to do as little as possible while
remaining highly effective.

Falcon apps work with any WSGI server, and run like a champ under
CPython 2.7, CPython 3.5+, PyPy2.7, and PyPy3.5.

.. Patron list starts here. For Python package, we substitute this section with:
   Support Falcon Development
   --------------------------

A Big Thank You to Our Patrons
------------------------------

Platinum

.. raw:: html

    <p>
    <a href="https://www.govcert.lu/"><img src="https://falconframework.org/img/sponsors/govcert.png" height="60" alt="CERT Gouvernemental Luxembourg" ></a>
     </p>

Gold

.. raw:: html

    <p>
    <a href="https://www.likalo.com/"><img src="https://falconframework.org/img/sponsors/likalo.svg" height="20" alt="LIKALO" ></a>&nbsp;&nbsp;&nbsp;
    <a href="https://www.luhnar.com/"><img src="https://falconframework.org/img/sponsors/luhnar-dark.svg" height="16" alt="Luhnar Site Accelerator" style="padding-bottom: 2px"></a>
     </p>

Silver

.. raw:: html

    <p>
    <a href="https://www.pnk.sh/python-falcon" target="_blank"><img src="https://falconframework.org/img/sponsors/paris.svg" height="20" alt="Paris Kejser"></a>
    </p>

.. Patron list ends here (see the comment above this section).

Has Falcon helped you make an awesome app? Show your support today with a one-time donation or by becoming a patron. Supporters get cool gear, an opportunity to promote their brand to Python developers, and
prioritized support.

`Learn how to support Falcon development <https://falconframework.org/#sectionSupportFalconDevelopment>`_

Thanks!

Quick Links
-----------

* `Read the docs <https://falcon.readthedocs.io/en/stable>`_
* `Falcon add-ons and complementary packages <https://github.com/falconry/falcon/wiki>`_
* `Falcon talks, podcasts, and blog posts <https://github.com/falconry/falcon/wiki/Talks-and-Podcasts>`_
* `falconry/user for Falcon users <https://gitter.im/falconry/user>`_ @ Gitter
* `falconry/dev for Falcon contributors <https://gitter.im/falconry/dev>`_ @ Gitter

What People are Saying
----------------------

"We have been using Falcon as a replacement for [framework] and we simply love the performance (three times faster) and code base size (easily half of our original [framework] code)."

"Falcon looks great so far. I hacked together a quick test for a
tiny server of mine and was ~40% faster with only 20 minutes of
work."

"Falcon is rock solid and it's fast."

"I'm loving #falconframework! Super clean and simple, I finally
have the speed and flexibility I need!"

"I feel like I'm just talking HTTP at last, with nothing in the
middle. Falcon seems like the requests of backend."

"The source code for Falcon is so good, I almost prefer it to
documentation. It basically can't be wrong."

"What other framework has integrated support for 786 TRY IT NOW ?"

How is Falcon Different?
------------------------

    Perfection is finally attained not when there is no longer anything
    to add, but when there is no longer anything to take away.

    *- Antoine de Saint-Exupéry*

We designed Falcon to support the demanding needs of large-scale
microservices and responsive app backends. Falcon complements more
general Python web frameworks by providing bare-metal performance,
reliability, and flexibility wherever you need it.

**Fast.** Same hardware, more requests. Falcon turns around
requests several times faster than most other Python frameworks. For
an extra speed boost, Falcon compiles itself with Cython when
available, and also works well with `PyPy <https://pypy.org>`__.
Considering a move to another programming language? Benchmark with
Falcon + PyPy first.

**Reliable.** We go to great lengths to avoid introducing
breaking changes, and when we do they are fully documented and only
introduced (in the spirit of
`SemVer <http://semver.org/>`__) with a major version
increment. The code is rigorously tested with numerous inputs and we
require 100% coverage at all times. Falcon does not depend on any
external Python packages.

**Flexible.** Falcon leaves a lot of decisions and implementation
details to you, the API developer. This gives you a lot of freedom to
customize and tune your implementation. Due to Falcon's minimalist
design, Python community members are free to independently innovate on
`Falcon add-ons and complementary packages <https://github.com/falconry/falcon/wiki>`__.

**Debuggable.** Falcon eschews magic. It's easy to tell which inputs
lead to which outputs. Unhandled exceptions are never encapsulated or
masked. Potentially surprising behaviors, such as automatic request body
parsing, are well-documented and disabled by default. Finally, when it
comes to the framework itself, we take care to keep logic paths simple
and understandable. All this makes it easier to reason about the code
and to debug edge cases in large-scale deployments.

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
-  CPython 2.7, CPython 3.5+, PyPy2.7, and PyPy3.5 support
-  ~20% speed boost under CPython when Cython is available

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
Both PyPy2.7 and PyPy3.5 are supported as of PyPy v5.10.

.. code:: bash

    $ pip install falcon

Or, to install the latest beta or release candidate, if any:

.. code:: bash

    $ pip install --pre falcon

CPython
^^^^^^^

Falcon also fully supports
`CPython <https://www.python.org/downloads/>`__ 2.7 and 3.5+.

A universal wheel is available on PyPI for the the Falcon framework.
Installing it is as simple as:

.. code:: bash

    $ pip install falcon

Installing the Falcon wheel is a great way to get up and running
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

If you want to verify that Cython is being invoked, simply
pass `-v` to pip in order to echo the compilation commands:

.. code:: bash

    $ pip install -v --no-binary :all: falcon

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
    $ pip install -r requirements/tests
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
        # NOTE: Starting with Falcon 1.3, you can simply
        # use req.media and resp.media for this instead.

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
                req.context.doc = json.loads(body.decode('utf-8'))

            except (ValueError, UnicodeDecodeError):
                raise falcon.HTTPError(falcon.HTTP_753,
                                       'Malformed JSON',
                                       'Could not decode the request body. The '
                                       'JSON was incorrect or not encoded as '
                                       'UTF-8.')

        def process_response(self, req, resp, resource):
            if not hasattr(resp.context, 'result'):
                return

            resp.body = json.dumps(resp.context.result)


    def max_body(limit):

        def hook(req, resp, resource, params):
            length = req.content_length
            if length is not None and length > limit:
                msg = ('The size of the request is too large. The body must not '
                       'exceed ' + str(limit) + ' bytes in length.')

                raise falcon.HTTPPayloadTooLarge(
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
            #
            # NOTE: Starting with Falcon 1.3, you can simply
            # use resp.media for this instead.
            resp.context.result = result

            resp.set_header('Powered-By', 'Falcon')
            resp.status = falcon.HTTP_200

        @falcon.before(max_body(64 * 1024))
        def on_post(self, req, resp, user_id):
            try:
                # NOTE: Starting with Falcon 1.3, you can simply
                # use req.media for this instead.
                doc = req.context.doc
            except AttributeError:
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
- John Vrbanac (**jmvrbanac** on GH and Gitter, and **jvrbanac** on Twitter)
- Vytautas Liuolia (**vytas7** on GH and Gitter)
- Nick Zaccardi (**nZac** on GH and Gitter)

Please don't hesitate to reach out if you have any questions, or just need a
little help getting started. You can find us in
`falconry/dev <https://gitter.im/falconry/dev>`_ on Gitter.

See also: `CONTRIBUTING.md <https://github.com/falconry/falcon/blob/master/CONTRIBUTING.md>`__

Legal
-----

Copyright 2013-2019 by Individual and corporate contributors as
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
.. |codecov.io| image:: https://codecov.io/gh/falconry/falcon/branch/master/graphs/badge.svg
   :target: http://codecov.io/gh/falconry/falcon
