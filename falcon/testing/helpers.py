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

"""Testing utilities.

This module contains various testing utilities that can be accessed
directly from the `testing` package::

    from falcon import testing

    wsgi_environ = testing.create_environ()
"""

import asyncio
import cgi
from collections import defaultdict
from collections import deque
import contextlib
from enum import Enum
import io
import itertools
import json
import random
import re
import socket
import sys
import time
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Union

import falcon
from falcon import errors as falcon_errors
from falcon.asgi_spec import EventType
from falcon.asgi_spec import ScopeType
from falcon.asgi_spec import WSCloseCode
from falcon.constants import SINGLETON_HEADERS
import falcon.request
from falcon.util import uri

# NOTE(kgriffs): Changed in 3.0 from 'curl/7.24.0 (x86_64-apple-darwin12.0)'
DEFAULT_UA = 'falcon-client/' + falcon.__version__
DEFAULT_HOST = 'falconframework.org'


class ASGILifespanEventEmitter:
    """Emits ASGI lifespan events to an ASGI app.

    This class can be used to drive a standard ASGI app callable in order to
    perform functional tests on the app in question.

    When simulating both lifespan and per-request events, each event stream
    will require a separate invocation of the ASGI callable; one with a
    lifespan event emitter, and one with a request event emitter. An
    asyncio :class:`~asyncio.Condition` can be used to pause the
    lifespan emitter until all of the desired request events have been
    emitted.

    Keyword Args:
        shutting_down (asyncio.Condition): An instance of
            :class:`asyncio.Condition` that will be awaited before
            emitting the final shutdown event (``'lifespan.shutdown``).
    """

    def __init__(self, shutting_down):
        self._state = 0
        self._shutting_down = shutting_down

    async def emit(self):
        if self._state == 0:
            self._state += 1
            return {'type': EventType.LIFESPAN_STARTUP}

        if self._state == 1:
            self._state += 1
            # NOTE(kgriffs): This verifies the app ignores events it does
            #   not recognize.
            return {'type': 'lifespan._nonstandard_event'}

        async with self._shutting_down:
            await self._shutting_down.wait()

        return {'type': EventType.LIFESPAN_SHUTDOWN}

    __call__ = emit


class ASGIRequestEventEmitter:
    """Emits events on-demand to an ASGI app.

    This class can be used to drive a standard ASGI app callable in order to
    perform functional tests on the app in question.

    Note:
        In order to ensure the app is able to handle subtle variations
        in the ASGI events that are allowed by the specification, such
        variations are applied to the emitted events at unspecified
        intervals. This includes whether or not the `more_body` field
        is explicitly set, or whether or not the request `body` chunk in
        the event is occasionally empty,

    Keyword Args:
        body (str): The body content to use when emitting http.request
            events. May be an empty string. If a byte string, it will
            be used as-is; otherwise it will be encoded as UTF-8
            (default ``b''``).
        chunk_size (int): The maximum number of bytes to include in
            a single http.request event (default 4096).
        disconnect_at (float): The Unix timestamp after which to begin
            emitting ``'http.disconnect'`` events (default now + 30s). The
            value may be either an ``int`` or a ``float``, depending
            on the precision required. Setting `disconnect_at` to
            ``0`` is treated as a special case, and will result in an
            ``'http.disconnect'`` event being immediately emitted (rather than
            first emitting an ``'http.request'`` event).

    Attributes:
        disconnected (bool): Returns ``True`` if the simulated client
            connection is in a "disconnected" state.
    """

    # TODO(kgriffs): If this pattern later becomes useful elsewhere,
    #   factor out into a standalone helper class.
    _branch_decider = defaultdict(bool)  # type: defaultdict

    def __init__(
        self,
        body: Union[str, bytes] = None,
        chunk_size: int = None,
        disconnect_at: Union[int, float] = None,
    ):
        if body is None:
            body = b''
        elif not isinstance(body, bytes):
            body = body.encode()

        body = memoryview(body)

        if disconnect_at is None:
            disconnect_at = time.time() + 30

        if chunk_size is None:
            chunk_size = 4096

        self._body = body  # type: Optional[memoryview]
        self._chunk_size = chunk_size
        self._emit_empty_chunks = True
        self._disconnect_at = disconnect_at
        self._disconnected = False
        self._exhaust_body = True

        self._emitted_empty_chunk_a = False
        self._emitted_empty_chunk_b = False

    @property
    def disconnected(self):
        return self._disconnected or (self._disconnect_at <= time.time())

    def disconnect(self, exhaust_body: bool = None):
        """Set the client connection state to disconnected.

        Call this method to simulate an immediate client disconnect and
        begin emitting ``'http.disconnect'`` events.

        Arguments:
            exhaust_body (bool): Set to ``False`` in order to
                begin emitting ``'http.disconnect'`` events without first
                emitting at least one ``'http.request'`` event.
        """

        if exhaust_body is not None:
            self._exhaust_body = exhaust_body

        self._disconnected = True

    async def emit(self) -> Dict[str, Any]:
        # NOTE(kgriffs): Special case: if we are immediately disconnected,
        #   the first event should be 'http.disconnnect'
        if self._disconnect_at == 0:
            return {'type': EventType.HTTP_DISCONNECT}

        #
        # NOTE(kgriffs): Based on my reading of the ASGI spec, at least one
        #   'http.request' event should be emitted before 'http.disconnect'
        #   for normal requests. However, the server may choose to
        #   immediately abandon a connection for some reason, in which case
        #   an 'http.request' event may never be sent.
        #
        #   See also: https://asgi.readthedocs.io/en/latest/specs/main.html#events
        #
        if self._body is None or not self._exhaust_body:
            # NOTE(kgriffs): When there are no more events, an ASGI
            #   server will hang until the client connection
            #   disconnects.
            while not self.disconnected:
                await asyncio.sleep(0.001)

            return {'type': EventType.HTTP_DISCONNECT}

        event = {'type': EventType.HTTP_REQUEST}  # type: Dict[str, Any]

        if self._emit_empty_chunks:
            # NOTE(kgriffs): Return a couple variations on empty chunks
            #   every time, to ensure test coverage.
            if not self._emitted_empty_chunk_a:
                self._emitted_empty_chunk_a = True
                event['more_body'] = True
                return event

            if not self._emitted_empty_chunk_b:
                self._emitted_empty_chunk_b = True
                event['more_body'] = True
                event['body'] = b''
                return event

            # NOTE(kgriffs): Part of the time just return an
            #   empty chunk to make sure the app handles that
            #   correctly.
            if self._toggle_branch('return_empty_chunk'):
                event['more_body'] = True

                # NOTE(kgriffs): Since ASGI specifies that
                #   'body' is optional, we toggle whether
                #   or not to explicitly set it to b'' to ensure
                #   the app handles both correctly.
                if self._toggle_branch('explicit_empty_body_1'):
                    event['body'] = b''

                return event

        chunk = self._body[: self._chunk_size]
        self._body = self._body[self._chunk_size :] or None

        if chunk:
            event['body'] = bytes(chunk)
        elif self._toggle_branch('explicit_empty_body_2'):
            # NOTE(kgriffs): Since ASGI specifies that
            #   'body' is optional, we toggle whether
            #   or not to explicitly set it to b'' to ensure
            #   the app handles both correctly.
            event['body'] = b''

        if self._body:
            event['more_body'] = True
        elif self._toggle_branch('set_more_body_false'):
            # NOTE(kgriffs): The ASGI spec allows leaving off
            #   the 'more_body' key when it would be set to
            #   False, so toggle one of the approaches
            #   to make sure the app handles both cases.
            event['more_body'] = False

        return event

    __call__ = emit

    def _toggle_branch(self, name: str):
        self._branch_decider[name] = not self._branch_decider[name]
        return self._branch_decider[name]


class ASGIResponseEventCollector:
    """Collects and validates ASGI events returned by an app.

    Attributes:
        events (iterable): An iterable of events that were emitted by
            the app, collected as-is from the app.
        headers (iterable): An iterable of (str, str) tuples representing
            the ISO-8859-1 decoded headers emitted by the app in the body of
            the ``'http.response.start'`` event.
        status (int): HTTP status code emitted by the app in the body of
            the ``'http.response.start'`` event.
        body_chunks (iterable): An iterable of ``bytes`` objects emitted
            by the app via ``'http.response.body'`` events.
        more_body (bool): Whether or not the app expects to emit more
            body chunks. Will be ``None`` if unknown (i.e., the app has
            not yet emitted any ``'http.response.body'`` events.)

    Raises:
        TypeError: An event field emitted by the app was of an unexpected type.
        ValueError: Invalid event name or field value.
    """

    _LIFESPAN_EVENT_TYPES = frozenset(
        [
            'lifespan.startup.complete',
            'lifespan.startup.failed',
            'lifespan.shutdown.complete',
            'lifespan.shutdown.failed',
        ]
    )

    _HEADER_NAME_RE = re.compile(rb'^[a-zA-Z][a-zA-Z0-9\-_]*$')
    _BAD_HEADER_VALUE_RE = re.compile(rb'[\000-\037]')

    def __init__(self):
        self.events = []
        self.headers = []
        self.status = None
        self.body_chunks = []
        self.more_body = None

    async def collect(self, event: Dict[str, Any]):
        if self.more_body is False:
            # NOTE(kgriffs): According to the ASGI spec, once we get a
            #   message setting more_body to False, any further messages
            #   on the channel are ignored.
            return

        self.events.append(event)

        event_type = event['type']
        if not isinstance(event_type, str):
            raise TypeError('ASGI event type must be a Unicode string')

        if event_type == EventType.HTTP_RESPONSE_START:
            for name, value in event.get('headers', []):
                if not isinstance(name, bytes):
                    raise TypeError('ASGI header names must be byte strings')
                if not isinstance(value, bytes):
                    raise TypeError('ASGI header names must be byte strings')

                # NOTE(vytas): Ported basic validation from wsgiref.validate.
                if not self._HEADER_NAME_RE.match(name):
                    raise ValueError('Bad header name: {!r}'.format(name))
                if self._BAD_HEADER_VALUE_RE.search(value):
                    raise ValueError('Bad header value: {!r}'.format(value))

                # NOTE(vytas): After the name validation above, the name is
                #   guaranteed to only contain a subset of ASCII.
                name_decoded = name.decode()
                if not name_decoded.islower():
                    raise ValueError('ASGI header names must be lowercase')

                self.headers.append((name_decoded, value.decode('latin1')))

            self.status = event['status']

            if not isinstance(self.status, int):
                raise TypeError('ASGI status must be an int')

        elif event_type == EventType.HTTP_RESPONSE_BODY:
            chunk = event.get('body', b'')
            if not isinstance(chunk, bytes):
                raise TypeError('ASGI body content must be a byte string')

            self.body_chunks.append(chunk)

            self.more_body = event.get('more_body', False)
            if not isinstance(self.more_body, bool):
                raise TypeError('ASGI more_body flag must be a bool')

        elif event_type not in self._LIFESPAN_EVENT_TYPES:
            raise ValueError('Invalid ASGI event type: ' + event_type)

    __call__ = collect


_WebSocketState = Enum('_WebSocketState', 'CONNECT HANDSHAKE ACCEPTED DENIED CLOSED')


class ASGIWebSocketSimulator:
    """Simulates a WebSocket client for testing a Falcon ASGI app.

    This class provides a way to test WebSocket endpoints in a Falcon ASGI app
    without having to interact with an actual ASGI server. While it is certainly
    important to test against a real server, a number of functional tests can be
    satisfied more efficiently and transparently with a simulated connection.

    Note:

        The ASGIWebSocketSimulator class is not designed to be instantiated
        directly; rather it should be obtained via
        :meth:`~falcon.testing.ASGIConductor.simulate_ws`.

    Attributes:
        ready (bool): ``True`` if the WebSocket connection has been
            accepted and the client is still connected, ``False`` otherwise.
        closed (bool): ``True`` if the WebSocket connection has been
            denied or closed by the app, or the client has disconnected.
        close_code (int): The WebSocket close code provided by the app if
            the connection is closed, or ``None`` if the connection is open.
        subprotocol (str): The subprotocol the app wishes to accept, or
            ``None`` if not specified.
        headers (Iterable[Iterable[bytes]]): An iterable of ``[name, value]``
            two-item iterables, where *name* is the header name, and *value* is
            the header value for each header returned by the app when
            it accepted the WebSocket connection. This property resolves to
            ``None`` if the connection has not been accepted.
    """

    def __init__(self):
        self.__msgpack = None

        self._state = _WebSocketState.CONNECT
        self._disconnect_emitted = False
        self._close_code = None
        self._accepted_subprotocol = None
        self._accepted_headers = None
        self._collected_server_events = deque()
        self._collected_client_events = deque()

        self._event_handshake_complete = asyncio.Event()

    @property
    def ready(self) -> bool:
        return self._state == _WebSocketState.ACCEPTED

    @property
    def closed(self) -> bool:
        return self._state in {_WebSocketState.DENIED, _WebSocketState.CLOSED}

    @property
    def close_code(self) -> int:
        return self._close_code

    @property
    def subprotocol(self) -> str:
        return self._accepted_subprotocol

    @property
    def headers(self) -> Iterable[Iterable[bytes]]:
        return self._accepted_headers

    async def wait_ready(self, timeout: Optional[int] = 5):
        """Wait until the connection has been accepted or denied.

        This coroutine can be awaited in order to pause execution until the
        app has accepted or denied the connection. In the latter case, an
        error will be raised to the caller.

        Keyword Args:
            timeout (int): Number of seconds to wait before giving up and
                raising an error (default: ``5``).
        """

        try:
            await asyncio.wait_for(self._event_handshake_complete.wait(), timeout)
        except asyncio.TimeoutError:
            msg = (
                'Timed out after waiting {} seconds for '
                'the WebSocket handshake to complete. Check the '
                'on_websocket responder and '
                'any middleware for any conditions that may be stalling the '
                'request flow.'
            ).format(timeout)
            raise asyncio.TimeoutError(msg)

        self._require_accepted()

    # NOTE(kgriffs): This is a coroutine just in case we need it to be
    #   in a future code revision. It also makes it more consistent
    #   with the other methods.
    async def close(self, code: Optional[int] = None):
        """Close the simulated connection.

        Keyword Args:
            code (int): The WebSocket close code to send to the application
                per the WebSocket spec (default: ``1000``).
        """

        # NOTE(kgriffs): Give our collector a chance in case the
        #   server is trying to close at the same time (e.g., there was an
        #   unhandled error and the server wants to disconnect with an error
        #   code.) We await a few times to let the server app settle across
        #   multiple of its own await's.
        for __ in range(3):
            await asyncio.sleep(0)

        if self.closed:
            return

        assert self._close_code is None

        if code is None:
            code = WSCloseCode.NORMAL

        self._state = _WebSocketState.CLOSED
        self._close_code = code

    async def send_text(self, payload: str):
        """Send a message to the app with a Unicode string payload.

        Arguments:
            payload (str): The string to send.
        """

        # NOTE(kgriffs): We have to check ourselves because some ASGI
        #   servers are not very strict which can lead to hard-to-debug
        #   errors.
        if not isinstance(payload, str):
            raise TypeError('payload must be a string')

        # NOTE(kgriffs): From the client's perspective, it was a send,
        #   but the server will be expecting websocket.receive
        await self._send(text=payload)

    async def send_data(self, payload: Union[bytes, bytearray, memoryview]):
        """Send a message to the app with a binary data payload.

        Arguments:
            payload (Union[bytes, bytearray, memoryview]): The binary data to send.
        """

        # NOTE(kgriffs): We have to check ourselves because some ASGI
        #   servers are not very strict which can lead to hard-to-debug
        #   errors.
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError('payload must be a byte string')

        # NOTE(kgriffs): From the client's perspective, it was a send,
        #   but the server will be expecting websocket.receive
        await self._send(data=bytes(payload))

    async def send_json(self, media: object):
        """Send a message to the app with a JSON-encoded payload.

        Arguments:
            media: A JSON-encodable object to send as a TEXT (0x01) payload.
        """

        text = json.dumps(media)
        await self.send_text(text)

    async def send_msgpack(self, media: object):
        """Send a message to the app with a MessagePack-encoded payload.

        Arguments:
            media: A MessagePack-encodable object to send as a BINARY (0x02) payload.
        """

        data = self._msgpack.packb(media, use_bin_type=True)
        await self.send_data(data)

    async def receive_text(self) -> str:
        """Receive a message from the app with a Unicode string payload.

        Awaiting this coroutine will block until a message is available or
        the WebSocket is disconnected.
        """

        event = await self._receive()

        # PERF(kgriffs): When we normally expect the key to be
        #   present, this pattern is faster than get()
        try:
            text = event['text']
        except KeyError:
            text = None

        # NOTE(kgriffs): Even if the key is present, it may be None
        if text is None:
            raise falcon_errors.PayloadTypeError(
                'Expected TEXT payload but got BINARY instead'
            )

        return text

    async def receive_data(self) -> bytes:
        """Receive a message from the app with a binary data payload.

        Awaiting this coroutine will block until a message is available or
        the WebSocket is disconnected.
        """

        event = await self._receive()

        # PERF(kgriffs): When we normally expect the key to be
        #   present, EAFP is faster than get()
        try:
            data = event['bytes']
        except KeyError:
            data = None

        # NOTE(kgriffs): Even if the key is present, it may be None
        if data is None:
            raise falcon_errors.PayloadTypeError(
                'Expected BINARY payload but got TEXT instead'
            )

        return data

    async def receive_json(self) -> object:
        """Receive a message from the app with a JSON-encoded TEXT payload.

        Awaiting this coroutine will block until a message is available or
        the WebSocket is disconnected.
        """

        text = await self.receive_text()
        return json.loads(text)

    async def receive_msgpack(self) -> object:
        """Receive a message from the app with a MessagePack-encoded BINARY payload.

        Awaiting this coroutine will block until a message is available or
        the WebSocket is disconnected.
        """

        data = await self.receive_data()
        return self._msgpack.unpackb(data, use_list=True, raw=False)

    @property
    def _msgpack(self):
        # NOTE(kgriffs): A property is used in lieu of referencing
        #   the msgpack module directly, in order to bubble up the
        #   import error in an obvious way, when the package has
        #   not been installed.

        if not self.__msgpack:
            import msgpack

            self.__msgpack = msgpack

        return self.__msgpack

    def _require_accepted(self):
        if self._state == _WebSocketState.ACCEPTED:
            return

        if self._state in {_WebSocketState.CONNECT, _WebSocketState.HANDSHAKE}:
            raise falcon_errors.OperationNotAllowed(
                'WebSocket connection has not yet been accepted'
            )
        elif self._state == _WebSocketState.CLOSED:
            raise falcon_errors.WebSocketDisconnected(self._close_code)

        assert self._state == _WebSocketState.DENIED

        if self._close_code == WSCloseCode.PATH_NOT_FOUND:
            raise falcon_errors.WebSocketPathNotFound(WSCloseCode.PATH_NOT_FOUND)

        if self._close_code == WSCloseCode.SERVER_ERROR:
            raise falcon_errors.WebSocketServerError(WSCloseCode.SERVER_ERROR)

        if self._close_code == WSCloseCode.HANDLER_NOT_FOUND:
            raise falcon_errors.WebSocketHandlerNotFound(WSCloseCode.HANDLER_NOT_FOUND)

        raise falcon_errors.WebSocketDisconnected(self._close_code)

    # NOTE(kgriffs): This is a coroutine just in case we need it to be
    #   in a future code revision. It also makes it more consistent
    #   with the other methods.
    async def _send(self, data: bytes = None, text: str = None):
        self._require_accepted()

        # NOTE(kgriffs): From the client's perspective, it was a send,
        #   but the server will be expecting websocket.receive
        event = {'type': EventType.WS_RECEIVE}  # type: Dict[str, Union[bytes, str]]

        if data is not None:
            event['bytes'] = data

        if text is not None:
            event['text'] = text

        self._collected_client_events.append(event)

        # NOTE(kgriffs): If something is waiting to read this data on the
        #   other side, give it a chance to progress (because we like to party
        #   like it's 1992.)
        await asyncio.sleep(0)

    async def _receive(self) -> Dict[str, Any]:
        while not self._collected_server_events:
            self._require_accepted()
            await asyncio.sleep(0)

        self._require_accepted()
        return self._collected_server_events.popleft()

    async def _emit(self) -> Dict[str, Any]:
        if self._state == _WebSocketState.CONNECT:
            self._state = _WebSocketState.HANDSHAKE
            return {'type': EventType.WS_CONNECT}

        if self._state == _WebSocketState.HANDSHAKE:
            # NOTE(kgriffs): We need to wait for the handshake to
            #   complete, before proceeding.
            await self._event_handshake_complete.wait()

        while not self._collected_client_events:
            await asyncio.sleep(0)
            if self.closed:
                return self._create_checked_disconnect()

        return self._collected_client_events.popleft()

    async def _collect(self, event: Dict[str, Any]):
        assert event

        if self._state == _WebSocketState.CONNECT:
            raise falcon_errors.OperationNotAllowed(
                'An ASGI application must receive the first websocket.connect '
                'event before attempting to send any events.'
            )

        event_type = event['type']
        if self._state == _WebSocketState.HANDSHAKE:
            if event_type == EventType.WS_ACCEPT:
                self._state = _WebSocketState.ACCEPTED
                self._accepted_subprotocol = event.get('subprotocol')
                self._accepted_headers = event.get('headers')
                self._event_handshake_complete.set()

                # NOTE(kgriffs): Yield to other pending tasks that may be
                #   waiting on the completion of the handshake. This ensures
                #   that the simulated client connection can enter its context
                #   before the app logic continues and potentially closes the
                #   connection from that side.
                await asyncio.sleep(0)

            elif event_type == EventType.WS_CLOSE:
                self._state = _WebSocketState.DENIED

                desired_code = event.get('code', WSCloseCode.NORMAL)
                if desired_code == WSCloseCode.SERVER_ERROR or (
                    3000 <= desired_code < 4000
                ):
                    # NOTE(kgriffs): Pass this code through since it is a
                    #   special code we have set in the framework to trigger
                    #   different raised error types or to pass through a
                    #   raised HTTPError status code.
                    self._close_code = desired_code
                else:
                    # NOTE(kgriffs): Force the close code to this since it is
                    #   similar to what happens with a real web server (the HTTP
                    #   connection is closed with a 403 and there is no websocket
                    #   close code).
                    self._close_code = WSCloseCode.FORBIDDEN

                self._event_handshake_complete.set()

            else:
                raise falcon_errors.OperationNotAllowed(
                    'An ASGI application must send either websocket.accept or '
                    'websocket.close before sending any other event types (got '
                    '{0})'.format(event_type)
                )

        elif self._state == _WebSocketState.ACCEPTED:
            if event_type == EventType.WS_CLOSE:
                self._state = _WebSocketState.CLOSED
                self._close_code = event.get('code', WSCloseCode.NORMAL)
            else:
                assert event_type == EventType.WS_SEND
                self._collected_server_events.append(event)
        else:
            assert self.closed

            # NOTE(kgriffs): According to the ASGI spec, we are
            #   supposed to just silently eat events once the
            #   socket is disconnected.
            pass

        # NOTE(kgriffs): Give whatever is waiting on the handshake or a
        #   collected data/text event a chance to progress.
        await asyncio.sleep(0)

    def _create_checked_disconnect(self) -> Dict[str, Any]:
        if self._disconnect_emitted:
            raise falcon_errors.OperationNotAllowed(
                'The websocket.disconnect event has already been emitted, '
                'and so the app should not attempt to receive any more '
                'events, since ASGI servers will likely block indefinitely '
                'rather than re-emitting websocket.disconnect events.'
            )

        self._disconnect_emitted = True
        return {'type': EventType.WS_DISCONNECT, 'code': self._close_code}


# get_encoding_from_headers() is Copyright 2016 Kenneth Reitz, and is
# used here under the terms of the Apache License, Version 2.0.
def get_encoding_from_headers(headers):
    """Return encoding from given HTTP Header Dict.

    Args:
        headers(dict): Dictionary from which to extract encoding. Header
            names must either be lowercase or the dict must support
            case-insensitive lookups.
    """

    content_type = headers.get('content-type')

    if not content_type:
        return None

    content_type, params = cgi.parse_header(content_type)

    if 'charset' in params:
        return params['charset'].strip('\'"')

    # NOTE(kgriffs): Added checks for text/event-stream and application/json
    if content_type in ('text/event-stream', 'application/json'):
        return 'UTF-8'

    if 'text' in content_type:
        return 'ISO-8859-1'

    return None


def get_unused_port() -> int:
    """Get an unused localhost port for use by a test server.

    Warning:
        It is possible for a third party to bind to the returned port
        before the caller is able to do so. The caller will need to
        retry with a different port in that case.

    Warning:
        This method has only be tested on POSIX systems and may not
        work elsewhere.
    """

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]


def rand_string(min, max) -> str:
    """Return a randomly-generated string, of a random length.

    Args:
        min (int): Minimum string length to return, inclusive
        max (int): Maximum string length to return, inclusive

    """

    int_gen = random.randint
    string_length = int_gen(min, max)
    return ''.join([chr(int_gen(ord(' '), ord('~'))) for __ in range(string_length)])


def create_scope(
    path='/',
    query_string='',
    method='GET',
    headers=None,
    host=DEFAULT_HOST,
    scheme=None,
    port=None,
    http_version='1.1',
    remote_addr=None,
    root_path=None,
    content_length=None,
    include_server=True,
    cookies=None,
) -> Dict[str, Any]:

    """Create a mock ASGI scope ``dict`` for simulating HTTP requests.

    Keyword Args:
        path (str): The path for the request (default ``'/'``)
        query_string (str): The query string to simulate, without a
            leading ``'?'`` (default ``''``). The query string is passed as-is
            (it will not be percent-encoded).
        method (str): The HTTP method to use (default ``'GET'``)
        headers (dict): Headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). When the
            request will include a body, the Content-Length header should be
            included in this list. Header names are not case-sensitive.

            Note:
                If a User-Agent header is not provided, it will default to::

                    f'falcon-client/{falcon.__version__}'

        host(str): Hostname for the request (default ``'falconframework.org'``).
            This also determines the value of the Host header in the
            request.
        scheme (str): URL scheme, either ``'http'`` or ``'https'``
            (default ``'http'``)
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for ``'http'``
            and 443 for ``'https'``). A string may also be passed, as long as
            it can be parsed as an int.
        http_version (str): The HTTP version to simulate. Must be either
            ``'2'``, ``'2.0'``, ``'1.1'``, ``'1.0'``, or ``'1'``
            (default ``'1.1'``). If set to ``'1.0'``, the Host header will not
            be added to the scope.
        remote_addr (str): Remote address for the request to use for
            the 'client' field in the connection scope (default None)
        root_path (str): The root path this application is mounted at; same as
            SCRIPT_NAME in WSGI (default ``''``).
        content_length (int): The expected content length of the request
            body (default ``None``). If specified, this value will be
            used to set the Content-Length header in the request.
        include_server (bool): Set to ``False`` to not set the 'server' key
            in the scope ``dict`` (default ``True``).
        cookies (dict): Cookies as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of items provides the name and value
            for the 'Set-Cookie' header.
    """

    http_version = _fixup_http_version(http_version)

    path = uri.decode(path, unquote_plus=False)

    # NOTE(kgriffs): Handles both None and ''
    query_string = query_string.encode() if query_string else b''

    if query_string and query_string.startswith(b'?'):
        raise ValueError("query_string should not start with '?'")

    scope = {
        'type': ScopeType.HTTP,
        'asgi': {
            'version': '3.0',
            'spec_version': '2.1',
        },
        'http_version': http_version,
        'method': method.upper(),
        'path': path,
        'query_string': query_string,
    }

    # NOTE(kgriffs): Explicitly test against None so that the caller
    #   is able to simulate setting app to an empty string if they
    #   need to cover that branch in their code.
    if root_path is not None:
        # NOTE(kgriffs): Judging by the algorithm given in PEP-3333 for
        #   reconstructing the URL, SCRIPT_NAME is expected to contain a
        #   preceding slash character. Since ASGI states that this value is
        #   the same as WSGI's SCRIPT_NAME, we will follow suit here.
        if root_path and not root_path.startswith('/'):
            scope['root_path'] = '/' + root_path
        else:
            scope['root_path'] = root_path

    if scheme:
        if scheme not in {'http', 'https', 'ws', 'wss'}:
            raise ValueError("scheme must be either 'http', 'https', 'ws', or 'wss'")

        scope['scheme'] = scheme

    if port is None:
        if (scheme or 'http') in {'http', 'ws'}:
            port = 80
        else:
            port = 443
    else:
        port = int(port)

    if remote_addr:
        # NOTE(kgriffs): Choose from the standard IANA dynamic range
        remote_port = random.randint(49152, 65535)

        # NOTE(kgriffs): Expose as an iterable to ensure the framework/app
        #   isn't hard-coded to only work with a list or tuple.
        scope['client'] = iter([remote_addr, remote_port])

    if include_server:
        scope['server'] = iter([host, port])

    # NOTE(myusko): Clients discard Set-Cookie header
    #  in the response to the OPTIONS method.
    if method == 'OPTIONS' and cookies is not None:
        cookies = None

    _add_headers_to_scope(
        scope, headers, content_length, host, port, scheme, http_version, cookies
    )

    return scope


def create_scope_ws(
    path='/',
    query_string='',
    headers=None,
    host=DEFAULT_HOST,
    scheme=None,
    port=None,
    http_version='1.1',
    remote_addr=None,
    root_path=None,
    include_server=True,
    subprotocols=None,
    spec_version='2.1',
) -> Dict[str, Any]:

    """Create a mock ASGI scope ``dict`` for simulating WebSocket requests.

    Keyword Args:
        path (str): The path for the request (default ``'/'``)
        query_string (str): The query string to simulate, without a
            leading ``'?'`` (default ``''``). The query string is passed as-is
            (it will not be percent-encoded).
        headers (dict): Headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). When the
            request will include a body, the Content-Length header should be
            included in this list. Header names are not case-sensitive.

            Note:
                If a User-Agent header is not provided, it will default to::

                    f'falcon-client/{falcon.__version__}'

        host(str): Hostname for the request (default ``'falconframework.org'``).
            This also determines the value of the Host header in the
            request.
        scheme (str): URL scheme, either ``'ws'`` or ``'wss'``
            (default ``'ws'``)
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for ``'ws'``
            and 443 for ``'wss'``). A string may also be passed, as long as
            it can be parsed as an int.
        http_version (str): The HTTP version to simulate. Must be either
            ``'2'``, ``'2.0'``, or ``'1.1'`` (default ``'1.1'``).
        remote_addr (str): Remote address for the request to use for
            the 'client' field in the connection scope (default None)
        root_path (str): The root path this application is mounted at; same as
            SCRIPT_NAME in WSGI (default ``''``).
        include_server (bool): Set to ``False`` to not set the 'server' key
            in the scope ``dict`` (default ``True``).
        spec_version (str): The ASGI spec version to emulate (default ``'2.1'``).
        subprotocols (Iterable[str]): Subprotocols the client wishes to
            advertise to the server (default ``[]``).
    """

    scope = create_scope(
        path=path,
        query_string=query_string,
        headers=headers,
        host=host,
        scheme=(scheme or 'ws'),
        port=port,
        http_version=http_version,
        remote_addr=remote_addr,
        root_path=root_path,
        include_server=include_server,
    )

    scope['type'] = ScopeType.WS
    scope['asgi']['spec_version'] = spec_version
    del scope['method']

    # NOTE(kgriffiths): Explicit check against None affords simulating a request
    #   with a scope that does not contain the optional 'subprotocols' key.
    if subprotocols is not None:
        scope['subprotocols'] = subprotocols

    return scope


def create_environ(
    path='/',
    query_string='',
    http_version='1.1',
    scheme='http',
    host=DEFAULT_HOST,
    port=None,
    headers=None,
    app=None,
    body='',
    method='GET',
    wsgierrors=None,
    file_wrapper=None,
    remote_addr=None,
    root_path=None,
    cookies=None,
) -> Dict[str, Any]:

    """Create a mock PEP-3333 environ ``dict`` for simulating WSGI requests.

    Keyword Args:
        path (str): The path for the request (default ``'/'``)
        query_string (str): The query string to simulate, without a
            leading ``'?'`` (default ``''``). The query string is passed as-is
            (it will not be percent-encoded).
        http_version (str): The HTTP version to simulate. Must be either
            ``'2'``, ``'2.0'``, ``'1.1'``, ``'1.0'``, or ``'1'``
            (default ``'1.1'``). If set to ``'1.0'``, the Host header will not
            be added to the scope.
        scheme (str): URL scheme, either ``'http'`` or ``'https'``
            (default ``'http'``)
        host(str): Hostname for the request (default ``'falconframework.org'``)
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for ``'http'``
            and 443 for ``'https'``). A string may also be passed, as long as
            it can be parsed as an int.
        headers (dict): Headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). Header names are not
            case-sensitive.

            Note:
                If a User-Agent header is not provided, it will default to::

                    f'falcon-client/{falcon.__version__}'

        root_path (str): Value for the ``SCRIPT_NAME`` environ variable, described in
            PEP-333: 'The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This may be an empty string, if the
            application corresponds to the "root" of the server.' (default ``''``)
        app (str): Deprecated alias for `root_path`. If both kwargs are passed,
            `root_path` takes precedence.
        body (str): The body of the request (default ``''``). The value will be
            encoded as UTF-8 in the WSGI environ. Alternatively, a byte string
            may be passed, in which case it will be used as-is.
        method (str): The HTTP method to use (default ``'GET'``)
        wsgierrors (io): The stream to use as *wsgierrors*
            (default ``sys.stderr``)
        file_wrapper: Callable that returns an iterable, to be used as
            the value for *wsgi.file_wrapper* in the environ.
        remote_addr (str): Remote address for the request to use as the
            ``'REMOTE_ADDR'`` environ variable (default ``None``)
        cookies (dict): Cookies as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of items provides the name and value
            for the Set-Cookie header.

    """

    http_version = _fixup_http_version(http_version)

    if query_string and query_string.startswith('?'):
        raise ValueError("query_string should not start with '?'")

    body = io.BytesIO(body.encode() if isinstance(body, str) else body)

    # NOTE(kgriffs): wsgiref, gunicorn, and uWSGI all unescape
    # the paths before setting PATH_INFO
    path = uri.decode(path, unquote_plus=False)

    # NOTE(kgriffs): The decoded path may contain UTF-8 characters.
    # But according to the WSGI spec, no strings can contain chars
    # outside ISO-8859-1. Therefore, to reconcile the URI
    # encoding standard that allows UTF-8 with the WSGI spec
    # that does not, WSGI servers tunnel the string via
    # ISO-8859-1. falcon.testing.create_environ() mimics this
    # behavior, e.g.:
    #
    #   tunnelled_path = path.encode('utf-8').decode('iso-8859-1')
    #
    # falcon.Request does the following to reverse the process:
    #
    #   path = tunnelled_path.encode('iso-8859-1').decode('utf-8', 'replace')
    #
    path = path.encode().decode('iso-8859-1')

    scheme = scheme.lower()
    if port is None:
        port = '80' if scheme == 'http' else '443'
    else:
        # NOTE(kgriffs): Running it through int() first ensures that if
        #   a string was passed, it is a valid integer.
        port = str(int(port))

    root_path = root_path or app or ''

    # NOTE(kgriffs): Judging by the algorithm given in PEP-3333 for
    # reconstructing the URL, SCRIPT_NAME is expected to contain a
    # preceding slash character.
    if root_path and not root_path.startswith('/'):
        root_path = '/' + root_path

    env = {
        'SERVER_PROTOCOL': 'HTTP/' + http_version,
        'SERVER_SOFTWARE': 'gunicorn/0.17.0',
        'SCRIPT_NAME': (root_path or ''),
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'REMOTE_PORT': '65133',
        'RAW_URI': '/',
        'SERVER_NAME': host,
        'SERVER_PORT': port,
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': scheme,
        'wsgi.input': body,
        'wsgi.errors': wsgierrors or sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False,
    }

    # NOTE(kgriffs): It has been observed that WSGI servers do not always
    #   set the REMOTE_ADDR variable, so we don't always set it either, to
    #   ensure the framework/app handles that case correctly.
    if remote_addr:
        env['REMOTE_ADDR'] = remote_addr

    if file_wrapper is not None:
        env['wsgi.file_wrapper'] = file_wrapper

    if http_version != '1.0':
        host_header = host

        if scheme == 'https':
            if port != '443':
                host_header += ':' + port
        else:
            if port != '80':
                host_header += ':' + port

        env['HTTP_HOST'] = host_header

    content_length = body.seek(0, 2)
    body.seek(0)

    if content_length != 0:
        env['CONTENT_LENGTH'] = str(content_length)

    # NOTE(myusko): Clients discard Set-Cookie header
    #  in the response to the OPTIONS method.
    if cookies is not None and method != 'OPTIONS':
        env['HTTP_COOKIE'] = _make_cookie_values(cookies)

    _add_headers_to_environ(env, headers)

    return env


def create_req(options=None, **kwargs) -> falcon.Request:
    """Create and return a new Request instance.

    This function can be used to conveniently create a WSGI environ
    and use it to instantiate a :py:class:`falcon.Request` object in one go.

    The arguments for this function are identical to those
    of :py:meth:`falcon.testing.create_environ`, except an additional
    `options` keyword argument may be set to an instance of
    :py:class:`falcon.RequestOptions` to configure certain
    aspects of request parsing in lieu of the defaults.
    """

    env = create_environ(**kwargs)
    return falcon.request.Request(env, options=options)


def create_asgi_req(body=None, req_type=None, options=None, **kwargs) -> falcon.Request:
    """Create and return a new ASGI Request instance.

    This function can be used to conveniently create an ASGI scope
    and use it to instantiate a :py:class:`falcon.asgi.Request` object
    in one go.

    The arguments for this function are identical to those
    of :py:meth:`falcon.testing.create_scope`, with the addition of
    `body`, `req_type`, and `options` arguments as documented below.

    Keyword Arguments:
        body (bytes): The body data to use for the request (default b''). If
            the value is a :py:class:`str`, it will be UTF-8 encoded to
            a byte string.
        req_type (object): A subclass of :py:class:`falcon.asgi.Request`
            to instantiate. If not specified, the standard
            :py:class:`falcon.asgi.Request` class will simply be used.
        options (falcon.RequestOptions): An instance of
            :py:class:`falcon.RequestOptions` that should be used to determine
            certain aspects of request parsing in lieu of the defaults.
    """

    scope = create_scope(**kwargs)

    body = body or b''
    disconnect_at = time.time() + 300

    req_event_emitter = ASGIRequestEventEmitter(body, disconnect_at=disconnect_at)

    # NOTE(kgriffs): Import here in case the app is running under
    #   Python 3.5 (in which case as long as it does not call the
    #   present function, it won't trigger an import error).
    import falcon.asgi

    req_type = req_type or falcon.asgi.Request
    return req_type(scope, req_event_emitter, options=options)


@contextlib.contextmanager
def redirected(stdout=sys.stdout, stderr=sys.stderr):
    """Redirect stdout or stderr temporarily.

    e.g.:

    with redirected(stderr=os.devnull):
        ...
    """

    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout, stderr
    try:
        yield
    finally:
        sys.stderr, sys.stdout = old_stderr, old_stdout


def closed_wsgi_iterable(iterable):
    """Wrap an iterable to ensure its ``close()`` method is called.

    Wraps the given `iterable` in an iterator utilizing a ``for`` loop as
    illustrated in
    `the PEP-3333 server/gateway side example
    <https://www.python.org/dev/peps/pep-3333/#the-server-gateway-side>`_.
    Finally, if the iterable has a ``close()`` method, it is called upon
    exception or exhausting iteration.

    Furthermore, the first bytestring yielded from iteration, if any, is
    prefetched before returning the wrapped iterator in order to ensure the
    WSGI ``start_response`` function is called even if the WSGI application is
    a generator.

    Args:
        iterable (iterable): An iterable that yields zero or more
            bytestrings, per PEP-3333

    Returns:
        iterator: An iterator yielding the same bytestrings as `iterable`
    """

    def wrapper():
        try:
            for item in iterable:
                yield item
        finally:
            if hasattr(iterable, 'close'):
                iterable.close()

    wrapped = wrapper()
    try:
        head = (next(wrapped),)
    except StopIteration:
        head = ()
    return itertools.chain(head, wrapped)


# ---------------------------------------------------------------------
# Private
# ---------------------------------------------------------------------


def _add_headers_to_environ(env, headers):
    if headers:
        try:
            items = headers.items()
        except AttributeError:
            items = headers

        for name, value in items:
            name_wsgi = name.upper().replace('-', '_')
            if name_wsgi not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                name_wsgi = 'HTTP_' + name_wsgi

            if value is None:
                value = ''
            else:
                value = value.strip()

            if name_wsgi not in env or name.lower() in SINGLETON_HEADERS:
                env[name_wsgi] = value
            else:
                env[name_wsgi] += ',' + value

    env.setdefault('HTTP_USER_AGENT', DEFAULT_UA)


def _add_headers_to_scope(
    scope, headers, content_length, host, port, scheme, http_version, cookies
):
    found_ua = False
    prepared_headers = []

    if headers:
        try:
            items = headers.items()
        except AttributeError:
            items = headers

        for name, value in items:
            n = name.lower().encode('latin1')
            found_ua = found_ua or (n == b'user-agent')

            # NOTE(kgriffs): Value is stripped if not empty, otherwise defaults
            #   to b'' to be consistent with _add_headers_to_environ().
            v = b'' if value is None else value.strip().encode('latin1')

            # NOTE(kgriffs): Expose as an iterable to ensure the framework/app
            #   isn't hard-coded to only work with a list or tuple.
            prepared_headers.append(iter([n, v]))

    if not found_ua:
        prepared_headers.append([b'user-agent', DEFAULT_UA.encode()])

    if content_length is not None:
        value = str(content_length).encode()
        prepared_headers.append((b'content-length', value))

    if http_version != '1.0':
        host_header = host

        if scheme == 'https':
            if port != 443:
                host_header += ':' + str(port)
        else:
            if port != 80:
                host_header += ':' + str(port)

        prepared_headers.append([b'host', host_header.encode()])

    if cookies is not None:
        prepared_headers.append([b'cookie', _make_cookie_values(cookies).encode()])

    # NOTE(kgriffs): Make it an iterator to ensure the app is not expecting
    #   a specific type (ASGI only specified that it is an iterable).
    scope['headers'] = iter(prepared_headers)


def _fixup_http_version(http_version) -> str:
    if http_version not in ('2', '2.0', '1.1', '1.0', '1'):
        raise ValueError('Invalid http_version specified: ' + http_version)

    # NOTE(kgrifs): Normalize so that they conform to the standard
    #   protocol names with prefixed with "HTTP/"
    if http_version == '2.0':
        http_version = '2'
    elif http_version == '1':
        http_version = '1.0'

    return http_version


def _make_cookie_values(cookies: Dict) -> str:
    return '; '.join(
        [
            '{}={}'.format(key, cookie.value if hasattr(cookie, 'value') else cookie)
            for key, cookie in cookies.items()
        ]
    )
