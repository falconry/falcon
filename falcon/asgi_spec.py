# Copyright 2020 by Kurt Griffiths
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

"""Constants, etc. defined by the ASGI specification."""

from __future__ import annotations

from typing import Any, Dict, Mapping


class EventType:
    """Standard ASGI event type strings."""

    HTTP_REQUEST = 'http.request'
    HTTP_RESPONSE_START = 'http.response.start'
    HTTP_RESPONSE_BODY = 'http.response.body'
    HTTP_DISCONNECT = 'http.disconnect'

    LIFESPAN_STARTUP = 'lifespan.startup'
    LIFESPAN_STARTUP_COMPLETE = 'lifespan.startup.complete'
    LIFESPAN_STARTUP_FAILED = 'lifespan.startup.failed'
    LIFESPAN_SHUTDOWN = 'lifespan.shutdown'
    LIFESPAN_SHUTDOWN_COMPLETE = 'lifespan.shutdown.complete'
    LIFESPAN_SHUTDOWN_FAILED = 'lifespan.shutdown.failed'

    WS_CONNECT = 'websocket.connect'
    WS_ACCEPT = 'websocket.accept'
    WS_RECEIVE = 'websocket.receive'
    WS_SEND = 'websocket.send'
    WS_DISCONNECT = 'websocket.disconnect'
    WS_CLOSE = 'websocket.close'


class ScopeType:
    """Standard ASGI event type strings."""

    HTTP = 'http'
    WS = 'websocket'
    LIFESPAN = 'lifespan'


class WSCloseCode:
    """WebSocket close codes used by the Falcon ASGI framework.

    See also: https://tools.ietf.org/html/rfc6455#section-7.4
    """

    NORMAL = 1000
    SERVER_ERROR = 1011
    FORBIDDEN = 3403
    PATH_NOT_FOUND = 3404
    HANDLER_NOT_FOUND = 3405


# TODO: use a typed dict for event dicts
AsgiEvent = Mapping[str, Any]
# TODO: use a typed dict for send msg dicts
AsgiSendMsg = Dict[str, Any]
