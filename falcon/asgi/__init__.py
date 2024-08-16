# Copyright 2019 by Kurt Griffiths.
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

"""ASGI package for Falcon, the minimalist web API framework.

The `falcon.asgi` package can be used to directly access most of
the framework's ASGI-related classes, functions, and variables::

    import falcon.asgi

    app = falcon.asgi.API()

Some ASGI-related methods and classes are found in other modules
(most notably falcon.testing) when their purpose is particularly cohesive with
that of the module in question.
"""

from .app import App
from .request import Request
from .response import Response
from .stream import BoundedStream
from .structures import SSEvent
from .ws import WebSocket
from .ws import WebSocketOptions

__all__ = (
    'App',
    'BoundedStream',
    'Request',
    'Response',
    'SSEvent',
    'WebSocket',
    'WebSocketOptions',
)
