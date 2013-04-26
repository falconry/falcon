<img align="right" src="http://c420059.r59.cf1.rackcdn.com/assets/images/falcon.png" alt="Falcon picture" />

Falcon [![Build Status](https://travis-ci.org/racker/falcon.png)](https://travis-ci.org/racker/falcon)
======

:runner: Come hang out with us in **#falconframework** on freenode.

Falcon is a [high-performance Python framework][home] for building cloud APIs. It tries to do as little as possible while remaining [highly effective][benefits].

> Perfection is finally attained not when there is no longer anything to add, but when there is no longer anything to take away.
>
> *- Antoine de Saint-Exupéry*

[home]: http://falconframework.org/index.html
[benefits]: http://falconframework.org/index.html#Benefits

### Design Goals ###

**Fast.** Cloud APIs need to turn around requests quickly, and make efficient use of hardware. This is particularly important when serving many concurrent requests. Falcon processes requests [several times faster][bench] than other popular web frameworks.

**Light.** Only the essentials are included, with *six* being the only dependency outside the standard library. We work to keep the code lean, making Falcon easier to test, optimize, and deploy.

**Flexible.** Falcon can be deployed in a variety of ways, depending on your needs. The framework speaks WSGI, and works great with [Python 2.6 and 2.7, PyPy, and Python 3.3][ci]. There's no tight coupling with any async framework, leaving you free to mix-and-match what you need.

[bench]: http://falconframework.org/#Metrics
[ci]: https://travis-ci.org/racker/falcon

### Features ###

* Intuitive routing via URI templates and resource classes
* Easy access to headers and bodies through request and response classes
* Idiomatic HTTP error responses via a handy exception base class
* DRY request processing using global, resource, and method hooks
* Snappy unit testing through WSGI helpers and mocks
* 20% speed boost when Cython is available
* Python 2.6, Python 2.7, PyPy and Python 3.3 support
* Speed, speed, and more speed!

### Install ###

```bash
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

Read the source, Luke!

Docstrings can be found throughout the Falcon code base for your learning pleasure. You can also ask questions in **#falconframework** on freenode. We are planning on having real docs eventually; if you need them right away, consider sending a pull request. ;)

Here is a simple example showing how to create a Falcon-based API.

```python
class ThingsResource:
    def on_get(self, req, resp):
        """Handles GET requests"""
        resp.status = falcon.HTTP_200
        resp.body = 'Hello world!'

# falcon.API instances are callable WSGI apps
wsgi_app = api = falcon.API()

# Resources are represented by long-lived class instances
things = ThingsResource()

# things will handle all requests to the '/things' URL path
api.add_route('/things', things)
```

Here is a more involved example, demonstrating getting headers and query parameters, handling errors, and reading/writing message bodies.

```python

import json
import logging

import falcon


class StorageEngine:
    pass


class StorageError(Exception):
    pass


def token_is_valid(token, user_id):
    return True  # Suuuuuure it's valid...


def auth(req, resp, params):
    # Alternatively, do this in middleware
    token = req.get_header('X-Auth-Token')

    if token is None:
        raise falcon.HTTPUnauthorized('Auth token required',
                                      'Please provide an auth token '
                                      'as part of the request',
                                      'http://docs.example.com/auth')

    if not token_is_valid(token, params['user_id']):
        raise falcon.HTTPUnauthorized('Authentication required',
                                      'The provided auth token is '
                                      'not valid. Please request a '
                                      'new token and try again.',
                                      'http://docs.example.com/auth')


def check_media_type(req, resp, params):
    if not req.client_accepts_json():
        raise falcon.HTTPUnsupportedMediaType(
            'Media Type not Supported',
            'This API only supports the JSON media type.',
            'http://docs.examples.com/api/json')


class ThingsResource:

    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('thingsapi.' + __name__)

    def on_get(self, req, resp, user_id):
        marker = req.get_param('marker', default='')
        limit = req.get_param_as_int('limit', default=50)

        try:
            result = self.db.get_things(marker, limit)
        except Exception as ex:
            self.logger.error(ex)

            description = ('Aliens have attacked our base! We will '
                           'be back as soon as we fight them off. '
                           'We appreciate your patience.')

            raise falcon.HTTPServiceUnavailable('Service Outage', description)

        resp.set_header('X-Powered-By', 'Donuts')
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(result)

    def on_post(self, req, resp, user_id):
        try:
            raw_json = req.stream.read()
        except Exception:
            raise falcon.HTTPError(falcon.HTTP_748,
                                   'Read Error',
                                   'Could not read the request body. Must be '
                                   'them ponies again.')

        try:
            thing = json.loads(raw_json, 'utf-8')
        except ValueError:
            raise falcon.HTTPError(falcon.HTTP_753,
                                   'Malformed JSON',
                                   'Could not decode the request body. The '
                                   'JSON was incorrect.')

        try:
            proper_thing = self.db.add_thing(thing)

        except StorageError:
            raise falcon.HTTPError(falcon.HTTP_725,
                                   'Database Error',
                                   "Sorry, couldn't write your thing to the "
                                   'database. It worked on my machine.')

        resp.status = falcon.HTTP_201
        resp.location = '/%s/things/%s' % (user_id, proper_thing.id)

wsgi_app = api = falcon.API(before=[auth, check_media_type])

db = StorageEngine()
things = ThingsResource(db)
api.add_route('/{user_id}/things', things)

```

### Contributing ###

Kurt Griffiths (kgriffs) is the creator and current maintainer of the Falcon framework. Pull requests are always welcome.

Before submitting a pull request, please ensure you have added/updated the appropriate tests (and that all existing tests still pass with your changes), and that your coding style follows PEP 8 and doesn't cause pyflakes to complain.

Commit messages should be formatted using [AngularJS conventions][ajs] (one-liners are OK for now but body and footer may be required as the project matures).

Comments follow [Google's style guide][goog-style-comments].

[ajs]: http://goo.gl/QpbS7
[goog-style-comments]: http://google-styleguide.googlecode.com/svn/trunk/pyguide.html#Comments

### Legal ###

Copyright 2013 by Rackspace Hosting, Inc.

Falcon image courtesy of [John O'Neill](https://commons.wikimedia.org/wiki/File:Brown-Falcon,-Vic,-3.1.2008.jpg).

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
