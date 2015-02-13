Falcon [![Build Status](https://travis-ci.org/racker/falcon.png)](https://travis-ci.org/racker/falcon) [![Coverage Status](https://coveralls.io/repos/racker/falcon/badge.png?branch=master)](https://coveralls.io/r/racker/falcon)
======

:runner: Come hang out with us in **#falconframework** on freenode.

Falcon is a [high-performance Python framework][home] for building cloud APIs. It encourages the REST architectural style, and tries to do as little as possible while remaining [highly effective][benefits].

> Perfection is finally attained not when there is no longer anything to add, but when there is no longer anything to take away.
>
> *- Antoine de Saint-Exupéry*

[home]: http://falconframework.org/index.html
[benefits]: http://falconframework.org/index.html#Benefits

<img align="right" src="http://falconframework.org/img/falcon.png" alt="Falcon picture" />

### Design Goals ###

**Fast.** Cloud APIs need to turn around requests quickly, and make efficient use of hardware. This is particularly important when serving many concurrent requests. Falcon processes requests [several times faster][bench] than other popular web frameworks.

**Light.** Only the essentials are included, with *six* and *mimeparse* being the only dependencies outside the standard library. We work to keep the code lean, making Falcon easier to test, optimize, and deploy.

**Flexible.** Falcon can be deployed in a variety of ways, depending on your needs. The framework speaks WSGI, and works great with [Python 2.6 and 2.7, PyPy, and Python 3.3/3.4][ci]. There's no tight coupling with any async framework, leaving you free to mix-and-match what you need.

[bench]: http://falconframework.org/#Metrics
[ci]: https://travis-ci.org/racker/falcon

### Features ###

* Highly-optimized, extensible code base 
* Intuitive routing via URI templates and resource classes
* Easy access to headers and bodies through request and response classes
* Does not use WebOb (some of us do indeed consider this a feature)
* Idiomatic HTTP error responses via a handy exception base class
* DRY request processing using global, resource, and method hooks
* Snappy unit testing through WSGI helpers and mocks
* Python 2.6, Python 2.7, PyPy and Python 3.3/3.4 support
* 20% speed boost when Cython is available

### Install ###

> This documentation targets the upcoming 0.2 release of Falcon,
> currently in beta and available on PyPI. You will need to use the
> ``--pre`` flag with pip in order to install the Falcon 0.2 betas
> and release candidates.

If available, Falcon will compile itself with Cython for an extra
speed boost. The following will make sure Cython is installed first, and
that you always have the latest and greatest.

```bash
$ pip install --upgrade cython falcon
```

**Installing on OS X Mavericks with Xcode 5.1**

Xcode Command Line Tools are required to compile Cython. Install them with
this command:

```bash
$ xcode-select --install
```

The Xcode 5.1 CLang compiler treats unrecognized command-line options as
errors; this can cause problems under Python 2.6, for example:

```bash
clang: error: unknown argument: '-mno-fused-madd' [-Wunused-command-line-argument-hard-error-in-future]
```

You can work around errors caused by unused arguments by setting some
environment variables:

```bash
$ export CFLAGS=-Qunused-arguments
$ export CPPFLAGS=-Qunused-arguments
$ pip install cython falcon
```

### Test ###

```bash
$ pip install -r tools/test-requires
$ pip install nose && nosetests
```

To test across all supported Python versions:

```bash
$ pip install tox && tox
```

### Usage ###

We have started documenting the library at http://falcon.readthedocs.org and we would of course greatly appreciate pull requests to help accelerate that effort.

The docstrings in the Falcon code base are quite extensive, and we recommend keeping a REPL running while learning the framework so that you can query the various modules and classes as you have questions.

The Falcon community maintains a mailing list that you can use to share
your ideas and ask questions about the framework. We use the appropriately
minimalistic [Librelist](http://librelist.com/) to host the discussions.

Subscribing is super easy and doesn't require any account setup. Simply
send an email to falcon@librelist.com and follow the instructions in the
reply. For more information about managing your subscription, check out
the [Librelist help page](http://librelist.com/help.html).

While we don't have an official code of conduct, we do expect everyone
who participates on the mailing list to act professionally, and lead
by example in encouraging constructive discussions. Each individual in
the community is responsible for creating a positive, constructive, and
productive culture.

[Discussions are archived](http://librelist.com/browser/falcon)
for posterity. 

Finally, you can always ask questions in **#falconframework** on freenode. The community is very friendly and helpful.

Here is a simple, contrived example showing how to create a Falcon-based API.

```python
# things.py

# Let's get this party started
import falcon


# Falcon follows the REST architectural style, meaning (among
# other things) that you think in terms of resources and state
# transitions, which map to HTTP verbs.
class ThingsResource:
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

```

You can run the above example using any WSGI server, such as uWSGI
or Gunicorn. For example:

```bash
$ pip install gunicorn
$ gunicorn things:app
```

Then, in another terminal:

```bash
$ curl localhost:8000/things
```

### A More Complex Example ###

Here is a more involved example that demonstrates reading headers and query parameters, handling errors, and working with request and response bodies.

```python
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
        token = req.get_header('X-Auth-Token')
        project = req.get_header('X-Project-ID')

        if token is None:
            description = ('Please provide an auth token '
                           'as part of the request.')

            raise falcon.HTTPUnauthorized('Auth token required',
                                          description,
                                          href='http://docs.example.com/auth')

        if not self._token_is_valid(token, project):
            description = ('The provided auth token is not valid. '
                           'Please request a new token and try again.')

            raise falcon.HTTPUnauthorized('Authentication required',
                                          description,
                                          href='http://docs.example.com/auth',
                                          scheme='Token; UUID')

    def _token_is_valid(self, token, project):
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
                'Service Outage',
                description,
                30)

        # An alternative way of doing DRY serialization would be to
        # create a custom class that inherits from falcon.Request. This
        # class could, for example, have an additional 'doc' property
        # that would serialize to JSON under the covers.
        req.context['result'] = result

        resp.set_header('X-Powered-By', 'Small Furry Creatures')
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

# Useful for debugging problems in your API; works with pdb.set_trace()
if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 8000, app)
    httpd.serve_forever()
```

### Contributing ###

Kurt Griffiths (kgriffs) is the creator and current maintainer of the
Falcon framework, with the generous help of a number of contributors. Pull requests are always welcome.

Before submitting a pull request, please ensure you have added/updated the appropriate tests (and that all existing tests still pass with your changes), and that your coding style follows PEP 8 and doesn't cause pyflakes to complain.

Commit messages should be formatted using [AngularJS conventions][ajs] (one-liners are OK for now but body and footer may be required as the project matures).

Comments follow [Google's style guide][goog-style-comments].

[ajs]: http://goo.gl/QpbS7
[goog-style-comments]: http://google-styleguide.googlecode.com/svn/trunk/pyguide.html#Comments

### Legal ###

Copyright 2013 by Rackspace Hosting, Inc.

Falcon image courtesy of [John O'Neill](https://commons.wikimedia.org/wiki/File:Brown-Falcon,-Vic,-3.1.2008.jpg).

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
