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

# Hoist classes and functions into the falcon namespace
# Explicitly list all export here, unless there are many export of the same type (example
# status codes, constans and errors)
from falcon.app import API
from falcon.app import App
from falcon.constants import *
from falcon.errors import *
from falcon.hooks import after
from falcon.hooks import before
from falcon.http_error import HTTPError
from falcon.http_status import HTTPStatus
from falcon.middleware import CORSMiddleware
from falcon.redirects import HTTPFound
from falcon.redirects import HTTPMovedPermanently
from falcon.redirects import HTTPPermanentRedirect
from falcon.redirects import HTTPSeeOther
from falcon.redirects import HTTPTemporaryRedirect
from falcon.request import Forwarded
from falcon.request import Request
from falcon.request import RequestOptions
from falcon.response import Response
from falcon.response import ResponseOptions
from falcon.status_codes import *
from falcon.stream import BoundedStream
# NOTE(kgriffs): Ensure that "from falcon import uri" will import
# the same front-door module as "import falcon.uri". This works by
# priming the import cache with the one we want.
import falcon.uri
from falcon.util import async_to_sync
from falcon.util import BufferedReader
from falcon.util import CaseInsensitiveDict
from falcon.util import code_to_http_status
from falcon.util import Context
from falcon.util import create_task
from falcon.util import deprecated
from falcon.util import deprecation
from falcon.util import dt_to_http
from falcon.util import ETag
from falcon.util import get_argnames
from falcon.util import get_bound_method
from falcon.util import get_http_status
from falcon.util import get_running_loop
from falcon.util import http_cookies
from falcon.util import http_date_to_dt
from falcon.util import http_now
from falcon.util import http_status_to_code
from falcon.util import IS_64_BITS
from falcon.util import is_python_func
from falcon.util import misc
from falcon.util import reader
from falcon.util import runs_sync
from falcon.util import secure_filename
from falcon.util import structures
from falcon.util import sync
from falcon.util import sync_to_async
from falcon.util import sys
from falcon.util import time
from falcon.util import TimezoneGMT
from falcon.util import to_query_str
from falcon.util import uri
from falcon.util import wrap_sync_to_async
from falcon.util import wrap_sync_to_async_unsafe
from falcon.version import __version__


# NOTE(kgriffs): Only to be used internally on the rare occasion that we
#   need to log something that we can't communicate any other way.
_logger = _logging.getLogger('falcon')
_logger.addHandler(_logging.NullHandler())
