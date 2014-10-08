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

* Intuitive routing via URI templates and resource classes
* Easy access to headers and bodies through request and response classes
* Idiomatic HTTP error responses via a handy exception base class
* DRY request processing using global, resource, and method hooks
* Snappy unit testing through WSGI helpers and mocks
* 20% speed boost when Cython is available
* Python 2.6, Python 2.7, PyPy and Python 3.3/3.4 support
* Speed, speed, and more speed!

### Install ###

```bash
$ pip install cython falcon
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
$ pip install nose && nosetests
```

To test across all supported Python versions:

```bash
$ pip install tox && tox
```

### Usage ###

We have started documenting the library at http://falcon.readthedocs.org and we would of course greatly appreciate pull requests to help accelerate that effort.

The docstrings in the Falcon code base are quite extensive, and we recommend keeping a REPL running while learning the framework so that you can query the various modules and classes as you have questions.

You can also check out [Marconi's WSGI driver](https://github.com/openstack/marconi/tree/master/marconi/queues/transport/wsgi) to get a feel for how you might
leverage Falcon in a real-world app.

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


class StorageEngine(object):
    def get_things(self, marker, limit):
        return []

    def add_thing(self, thing):
        return {'id': str(uuid.uuid4())}


class StorageError(Exception):
    @staticmethod
    def handle(ex, req, resp, params):
        description = ('Sorry, couldn\'t write your thing to the '
                       'database. It worked on my box.')

        raise falcon.HTTPError(falcon.HTTP_725,
                               'Database Error',
                               description)


class Proxy(object):
    def forward(self, req):
        return falcon.HTTP_503


class SinkAdapter(object):

    def __init__(self):
        self._proxy = Proxy()

    def __call__(self, req, resp, **kwargs):
        resp.status = self._proxy.forward(req)
        self.kwargs = kwargs


def token_is_valid(token, user_id):
    return True  # Suuuuuure it's valid...


def auth(req, resp, params):
    # Alternatively, use Talons or do this in WSGI middleware...
    token = req.get_header('X-Auth-Token')

    if token is None:
        description = ('Please provide an auth token '
                       'as part of the request.')

        raise falcon.HTTPUnauthorized('Auth token required',
                                      description,
                                      href='http://docs.example.com/auth')

    if not token_is_valid(token, params['user_id']):
        description = ('The provided auth token is not valid. '
                       'Please request a new token and try again.')

        raise falcon.HTTPUnauthorized('Authentication required',
                                      description,
                                      href='http://docs.example.com/auth',
                                      scheme='Token; UUID')


def check_media_type(req, resp, params):
    if not req.client_accepts_json:
        raise falcon.HTTPNotAcceptable(
            'This API only supports responses encoded as JSON.',
            href='http://docs.examples.com/api/json')

    if req.method in ('POST', 'PUT'):
        if not req.content_type == 'application/json':
            raise falcon.HTTPUnsupportedMediaType(
                'This API only supports requests encoded as JSON.',
                href='http://docs.examples.com/api/json')


def deserialize(req, resp, resource, params):
    # req.stream corresponds to the WSGI wsgi.input environ variable,
    # and allows you to read bytes from the request body.
    #
    # See also: PEP 3333
    body = req.stream.read()
    if not body:
        raise falcon.HTTPBadRequest('Empty request body',
                                    'A valid JSON document is required.')

    try:
        params['doc'] = json.loads(body.decode('utf-8'))

    except (ValueError, UnicodeDecodeError):
        raise falcon.HTTPError(falcon.HTTP_753,
                               'Malformed JSON',
                               'Could not decode the request body. The '
                               'JSON was incorrect or not encoded as UTF-8.')


def serialize(req, resp, resource):
    resp.body = json.dumps(req.context['doc'])


class ThingsResource:

    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('thingsapp.' + __name__)

    @falcon.after(serialize)
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
        req.context['doc'] = result

        resp.set_header('X-Powered-By', 'Small Furry Creatures')
        resp.status = falcon.HTTP_200

    @falcon.before(deserialize)
    def on_post(self, req, resp, user_id, doc):
        proper_thing = self.db.add_thing(doc)

        resp.status = falcon.HTTP_201
        resp.location = '/%s/things/%s' % (user_id, proper_thing['id'])


# Configure your WSGI server to load "things.app" (app is a WSGI callable)
app = falcon.API(before=[auth, check_media_type])

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
app.add_sink(sink, r'/v1/[charts|inventory]')

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
