# Copyright 2013 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Primary package for Falcon, the minimalist WSGI library.

Falcon is a minimalist WSGI library for building speedy web APIs and app
backends. The `falcon` package can be used to directly access most of
the framework's classes, functions, and variables::

    import falcon

    app = falcon.API()

"""

HTTP_METHODS = (
    'CONNECT',
    'DELETE',
    'GET',
    'HEAD',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
    'TRACE',
)

DEFAULT_MEDIA_TYPE = 'application/json; charset=UTF-8'


# Hoist classes and functions into the falcon namespace
from falcon.version import __version__  # NOQA
from falcon.api import API, DEFAULT_MEDIA_TYPE  # NOQA
from falcon.status_codes import *  # NOQA
from falcon.errors import *  # NOQA
from falcon.redirects import *  # NOQA
from falcon.http_error import HTTPError  # NOQA
from falcon.http_status import HTTPStatus  # NOQA

# NOTE(kgriffs): Ensure that "from falcon import uri" will import
# the same front-door module as "import falcon.uri". This works by
# priming the import cache with the one we want.
import falcon.uri  # NOQA

from falcon.util import *  # NOQA

from falcon.hooks import before, after  # NOQA
from falcon.request import Request, RequestOptions  # NOQA
from falcon.response import Response  # NOQA
