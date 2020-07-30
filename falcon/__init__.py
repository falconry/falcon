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

"""Primary package for Falcon, the minimalist web API framework.

Falcon is a minimalist web API framework for building speedy web APIs and app
backends. The `falcon` package can be used to directly access most of
the framework's classes, functions, and variables::

    import falcon

    app = falcon.App()

"""

import logging as _logging
import sys as _sys

# Hoist classes and functions into the falcon namespace
from falcon.version import __version__  # NOQA
from falcon.constants import *  # NOQA
from falcon.app import App, API  # NOQA
from falcon.status_codes import *  # NOQA
from falcon.errors import *  # NOQA
from falcon.redirects import *  # NOQA
from falcon.http_error import HTTPError  # NOQA
from falcon.http_status import HTTPStatus  # NOQA
from falcon.middlewares import CORSMiddleware  # NOQA

# NOTE(kgriffs): Ensure that "from falcon import uri" will import
# the same front-door module as "import falcon.uri". This works by
# priming the import cache with the one we want.
import falcon.uri  # NOQA

from falcon.util import *  # NOQA

from falcon.hooks import before, after  # NOQA
from falcon.request import Request, RequestOptions, Forwarded  # NOQA
from falcon.response import Response, ResponseOptions  # NOQA


ASGI_SUPPORTED = _sys.version_info.minor > 5
"""Set to ``True`` when ASGI is supported for the current Python version."""


# NOTE(kgriffs): Only to be used internally on the rare occasion that we
#   need to log something that we can't communicate any other way.
_logger = _logging.getLogger('falcon')
_logger.addHandler(_logging.NullHandler())
