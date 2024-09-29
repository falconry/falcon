from __future__ import annotations

import asyncio
import collections
from enum import auto
from enum import Enum
import re
from typing import Any, Deque, Dict, Iterable, Mapping, Optional, Tuple, Union

from falcon import errors
from falcon import media
from falcon import status_codes
from falcon._typing import AsgiReceive
from falcon._typing import AsgiSend
from falcon._typing import HeaderArg
from falcon.asgi_spec import AsgiEvent
from falcon.asgi_spec import AsgiSendMsg
from falcon.asgi_spec import EventType
from falcon.asgi_spec import WSCloseCode
from falcon.constants import WebSocketPayloadType
from falcon.util import misc

__all__ = ('WebSocket',)


class _WebSocketState(Enum):
    HANDSHAKE = auto()
    ACCEPTED = auto()
    CLOSED = auto()


_CLIENT_DISCONNECTED_CAUSE = re.compile(r'received (\d\d\d\d)')


class WebSocket:
    """Represents a single WebSocket connection with a client."""

    __slots__ = (
        '_asgi_receive',
        '_asgi_send',
        '_buffered_receiver',
        '_close_code',
        '_close_reasons',
        '_supports_accept_headers',
        '_supports_reason',
        '_mh_bin_deserialize',
        '_mh_bin_serialize',
        '_mh_text_deserialize',
        '_mh_text_serialize',
        '_state',
        'subprotocols',
    )

    _asgi_receive: AsgiReceive
    _asgi_send: AsgiSend
    _state: _WebSocketState
    _close_code: Optional[int]
    subprotocols: Tuple[str, ...]
    """The list of subprotocol strings advertised by the client, or an empty tuple if
    no subprotocols were specified.
    """

    def __init__(
        self,
        ver: str,
        scope: Dict[str, Any],
        receive: AsgiReceive,
        send: AsgiSend,
        media_handlers: Mapping[
            WebSocketPayloadType,
            Union[media.BinaryBaseHandlerWS, media.TextBaseHandlerWS],
        ],
        max_receive_queue: int,
        default_close_reasons: Dict[int, str],
    ):
        self._supports_accept_headers = ver != '2.0'
        self._supports_reason = _supports_reason(ver)

        # NOTE(kgriffs): Normalize the iterable to a stable tuple; note that
        #   ordering is significant, and so we preserve it here.
        self.subprotocols = tuple(scope.get('subprotocols', []))

        # TODO(kgriffs): Should we make the use of _BufferedReceiver
        #   configurable? For example, if the developer knows that
        #   they will be interleaving receives and sends, then they
        #   will be able to find out about the 'websocket.disconnect'
        #   event via one of their receive() calls, and there is no
        #   need for the added overhead.
        self._buffered_receiver = _BufferedReceiver(receive, max_receive_queue)
        if max_receive_queue > 0:
            self._asgi_receive = self._buffered_receiver.receive
        else:
            # NOTE(vytas): Pass through the receive callable bypassing the
            #   buffered receiver in the case max_receive_queue is set to 0.
            self._asgi_receive = receive
        self._asgi_send = send

        mh_text = media_handlers[WebSocketPayloadType.TEXT]
        self._mh_text_serialize = mh_text.serialize
        self._mh_text_deserialize = mh_text.deserialize

        mh_bin = media_handlers[WebSocketPayloadType.BINARY]
        self._mh_bin_serialize = mh_bin.serialize
        self._mh_bin_deserialize = mh_bin.deserialize

        self._close_reasons = default_close_reasons
        self._state = _WebSocketState.HANDSHAKE
        self._close_code = None

    @property
    def unaccepted(self) -> bool:
        """``True`` if the WebSocket connection has not yet been accepted,
        ``False`` otherwise.
        """  # noqa: D205
        return self._state == _WebSocketState.HANDSHAKE

    @property
    def closed(self) -> bool:
        """``True`` if the WebSocket connection has been closed by the server or the
        client has disconnected.
        """  # noqa: D205
        return (
            self._state == _WebSocketState.CLOSED
            or self._buffered_receiver.client_disconnected
        )

    @property
    def ready(self) -> bool:
        """``True`` if the WebSocket connection has been accepted and the client is
        still connected, ``False`` otherwise.
        """  # noqa: D205
        return (
            self._state == _WebSocketState.ACCEPTED
            and not self._buffered_receiver.client_disconnected
        )

    @property
    def supports_accept_headers(self) -> bool:
        """``True`` if the ASGI server hosting the app supports sending headers when
        accepting the WebSocket connection, ``False`` otherwise.
        """  # noqa: D205
        return self._supports_accept_headers

    async def accept(
        self,
        subprotocol: Optional[str] = None,
        headers: Optional[HeaderArg] = None,
    ) -> None:
        """Accept the incoming WebSocket connection.

        If, after examining the connection's attributes (headers, advertised
        subprotocols, etc.) the request should be accepted, the responder must
        first await this coroutine method to finalize the WebSocket handshake.
        Alternatively, the responder may deny the connection request by awaiting
        the :meth:`~.close` method.

        Keyword Arguments:
            subprotocol (str): The subprotocol the app wishes to accept,
                out of the list of protocols that the client suggested. If
                more than one of the suggested protocols is acceptable,
                the first one in the list from the client should be
                selected (see also: :attr:`~.subprotocols`).

                When left unspecified, a Sec-WebSocket-Protocol header will
                not be included in the response to the client. The
                client may choose to abandon the connection in this case,
                if it does not receive an explicit protocol selection.

            headers (HeaderArg): An iterable of ``(name: str, value: str)``
                two-item iterables, representing a collection of HTTP headers to
                include in the handshake response. Both *name* and *value* must
                be of type ``str`` and contain only US-ASCII characters.

                Alternatively, a dict-like object may be passed that implements
                an ``items()`` method.

                Note:
                    This argument is only supported for ASGI servers that
                    implement spec version 2.1 or better. If an app needs to
                    be compatible with multiple ASGI servers, it can
                    reference the :attr:`~.supports_accept_headers` property to
                    determine if the hosting server supports this feature.

        """

        if self.closed:
            raise errors.OperationNotAllowed(
                'accept() may not be called on a closed WebSocket connection'
            )

        if self._state != _WebSocketState.HANDSHAKE:
            raise errors.OperationNotAllowed(
                'accept() may only be called once on an open WebSocket connection'
            )

        event: Dict[str, Any] = {
            'type': EventType.WS_ACCEPT,
        }

        if subprotocol is not None:
            if not isinstance(subprotocol, str):
                raise ValueError('WebSocket subprotocol must be a string')

            event['subprotocol'] = subprotocol

        if headers:
            if not self._supports_accept_headers:
                raise errors.OperationNotAllowed(
                    'The ASGI server that is running this app '
                    'does not support accept headers.'
                )

            header_items = getattr(headers, 'items', None)
            if callable(header_items):
                headers_iterable: Iterable[tuple[str, str]] = header_items()
            else:
                headers_iterable = headers  # type: ignore[assignment]

            event['headers'] = parsed_headers = [
                (name.lower().encode('ascii'), value.encode('ascii'))
                for name, value in headers_iterable
            ]

            for name, __ in parsed_headers:
                if name == b'sec-websocket-protocol':
                    raise ValueError(
                        'Per the ASGI spec, the headers iterable must not '
                        'contain "sec-websocket-protocol". Instead, the '
                        'subprotocol argument can be used to indicate the '
                        'accepted protocol.'
                    )

        await self._send(event)
        self._state = _WebSocketState.ACCEPTED

        self._buffered_receiver.start()

        # NOTE(kgriffs): We have to buffer received events so that we
        #   will know when a disconnect happens and we can alert the app
        #   via falcon.errors.WebSocketDisconnected so that the app knows
        #   it should bail out if it is just emitting a series of messages
        #   without ever reading any from the client.
        #
        # TODO(kgriffs): Bring this use case to the attention of the
        #   ASGI spec committee and see if they can't come up with a better
        #   way to deal with this.

    async def close(
        self, code: Optional[int] = None, reason: Optional[str] = None
    ) -> None:
        """Close the WebSocket connection.

        This coroutine method sends a WebSocket ``CloseEvent`` to the client
        and then proceeds to actually close the connection.

        The responder can also use this method to deny a connection request
        simply by awaiting it instead of :meth:`~.accept`. In this case,
        the client will receive an HTTP 403 response to the handshake.

        Keyword Arguments:
            code (int): The close code to use for the ``CloseEvent``
                (default 1000). See also:
                https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code.
            reason(str): The string reason indicating why the server closed the
                connection. See also:
                https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/reason.

                If there is no reason provided, Falcon will try to
                automatically look it up from the above `code` and
                :attr:`~WebSocketOptions.default_close_reasons`.

        Note:
            The close `reason` will only be propagated if the ASGI app server
            supports this.

            Version ``2.3``\\+ of the
            `HTTP & WebSocket
            <https://asgi.readthedocs.io/en/latest/specs/www.html>`__ ASGI
            protocol is required for `reason`.
        """

        # NOTE(kgriffs): Do this first to be sure we clean things up
        #   in the case that we are going to raise an error next.
        await self._buffered_receiver.stop()

        if code is None:
            code = WSCloseCode.NORMAL
        elif not isinstance(code, int):
            raise ValueError('code must be an int')
        elif code < 1000:
            raise ValueError('Invalid close code. The value must be >= 1000')
        elif 1015 <= code <= 1999 or 1004 <= code <= 1006:
            raise ValueError('Invalid close code. Only unreserved codes may be used.')

        # NOTE(kgriffs): Only do this after we validate the code, to avoid
        #   masking errors.
        if self.closed:
            return

        response = {'type': EventType.WS_CLOSE, 'code': code}

        reason = reason or self._close_reasons.get(code)
        if reason and self._supports_reason:  # pragma: no py311 cover
            # NOTE(vytas): I have verified that the below line is covered both
            #   by multiple unit tests and E2E tests.
            #   However, it is erroneously reported as missing on CPython 3.11.
            response['reason'] = reason

        await self._asgi_send(response)

        self._state = _WebSocketState.CLOSED
        self._close_code = code

    async def send_media(
        self,
        media: object,
        payload_type: WebSocketPayloadType = WebSocketPayloadType.TEXT,
    ) -> None:
        """Send a serializable object to the client.

        The payload type determines the media handler that will be used
        to serialize the given object (see also: :ref:`ws_media_handlers`).

        Arguments:
            media (object): The object to send.

        Keyword Arguments:
            payload_type (falcon.WebSocketPayloadType): The payload type to
                use for the message (default ``falcon.WebSocketPayloadType.TEXT``).

                Must be one of:

                .. code:: python

                    falcon.WebSocketPayloadType.TEXT
                    falcon.WebSocketPayloadType.BINARY
        """

        self._require_accepted()

        if payload_type is WebSocketPayloadType.TEXT:
            await self._send(
                {
                    'type': EventType.WS_SEND,
                    'text': self._mh_text_serialize(media),
                }
            )
        else:
            await self._send(
                {
                    'type': EventType.WS_SEND,
                    'bytes': self._mh_bin_serialize(media),
                }
            )

    async def send_text(self, payload: str) -> None:
        """Send a message to the client with a Unicode string payload.

        Arguments:
            payload (str): The string to send.
        """

        self._require_accepted()
        # NOTE(kgriffs): We have to check ourselves because some ASGI
        #   servers are not very strict which can lead to hard-to-debug
        #   errors.
        if not isinstance(payload, str):
            raise TypeError('payload must be a string')

        await self._send(
            {
                'type': EventType.WS_SEND,
                'text': payload,
            }
        )

    async def send_data(self, payload: Union[bytes, bytearray, memoryview]) -> None:
        """Send a message to the client with a binary data payload.

        Arguments:
            payload (Union[bytes, bytearray, memoryview]): The binary data to send.
        """

        self._require_accepted()
        # NOTE(kgriffs): We have to check ourselves because some ASGI
        #   servers are not very strict which can lead to hard-to-debug
        #   errors.
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError('payload must be a byte string')

        await self._send(
            {
                'type': EventType.WS_SEND,
                'bytes': bytes(payload),
            }
        )

    async def receive_text(self) -> str:
        """Receive a message from the client with a Unicode string payload.

        Awaiting this coroutine will block until a message is available or
        the WebSocket is disconnected.
        """

        self._require_accepted()

        event = await self._receive()

        # PERF(kgriffs): When we normally expect the key to be
        #   present, this pattern is faster than get()
        try:
            text = event['text']
        except KeyError:
            text = None

        # NOTE(kgriffs): Even if the key is present, it may be None
        if text is None:
            raise errors.PayloadTypeError('Missing TEXT (0x01) payload')

        return text

    async def receive_data(self) -> bytes:
        """Receive a message from the client with a binary data payload.

        Awaiting this coroutine will block until a message is available or
        the WebSocket is disconnected.
        """

        self._require_accepted()

        event = await self._receive()

        # PERF(kgriffs): When we normally expect the key to be
        #   present, EAFP is faster than get()
        try:
            data = event['bytes']
        except KeyError:
            data = None

        # NOTE(kgriffs): Even if the key is present, it may be None
        if data is None:
            raise errors.PayloadTypeError('Missing BINARY (0x02) payload')

        return data

    async def receive_media(self) -> object:
        """Receive a deserialized object from the client.

        The incoming payload type determines the media handler that will be used
        to deserialize the object (see also: :ref:`ws_media_handlers`).
        """

        self._require_accepted()

        event = await self._receive()

        # NOTE(kgriffs): Most likely case is going to be JSON via text
        #   payload, so try that first.
        text = event.get('text')
        if text is not None:
            return self._mh_text_deserialize(text)

        # PERF(kgriffs): At this point there better be a 'bytes' key, so
        #   use EAFP this time.
        try:
            data = event['bytes']
        except KeyError:
            data = None

        # NOTE(kgriffs): Even if the key is present, it may be None
        if data is None:
            raise errors.PayloadTypeError(
                'Message did not contain either a TEXT (0x01) or BINARY (0x02) payload'
            )

        return self._mh_bin_deserialize(data)

    async def _send(self, msg: AsgiSendMsg) -> None:
        if self._buffered_receiver.client_disconnected:
            self._state = _WebSocketState.CLOSED
            self._close_code = self._buffered_receiver.client_disconnected_code

        if self._state == _WebSocketState.CLOSED:
            raise errors.WebSocketDisconnected(self._close_code)

        try:
            await self._asgi_send(msg)
        except Exception as ex:
            # NOTE(kgriffs): If uvicorn (or any other server that uses the
            #   the "websockets" library) allows exceptions to bubble up,
            #   we will have an error raised on client disconnect.
            #
            #   Daphne, on the other hand, does not raise an error but just
            #   eats the message. This approach is actually more in keeping
            #   with the ASGI spec, but poses its own challenges.

            translated_ex = self._translate_webserver_error(ex)
            if translated_ex:
                # NOTE(vytas): Mark WebSocket as closed if we catch an error
                #   upon sending. This is useful when not using the buffered
                #   receiver, and not receiving anything at the given moment.
                self._state = _WebSocketState.CLOSED
                if isinstance(translated_ex, errors.WebSocketDisconnected):
                    self._close_code = translated_ex.code

                # NOTE(vytas): Use the raise from form in order to preserve
                #   the traceback.
                raise translated_ex from ex

            # NOTE(kgriffs): Re-raise other errors directly so that we don't
            #   obscure the traceback.
            raise

    async def _receive(self) -> AsgiEvent:
        event = await self._asgi_receive()

        event_type = event['type']

        if event_type != EventType.WS_RECEIVE:
            # NOTE(kgriffs): Based on the ASGI spec, there are no other
            #   event types that should be emitted by the protocol server,
            #   but we sanity-check it here just in case.
            assert event_type == EventType.WS_DISCONNECT

            self._state = _WebSocketState.CLOSED
            self._close_code = event.get('code', WSCloseCode.NORMAL)
            raise errors.WebSocketDisconnected(self._close_code)

        return event

    def _require_accepted(self) -> None:
        if self._state == _WebSocketState.HANDSHAKE:
            raise errors.OperationNotAllowed(
                'WebSocket connection has not yet been accepted'
            )
        elif self._state == _WebSocketState.CLOSED:
            raise errors.WebSocketDisconnected(self._close_code)

    def _translate_webserver_error(self, ex: Exception) -> Optional[Exception]:
        s = str(ex)

        # NOTE(kgriffs): uvicorn or any other server using the "websockets"
        #   package that allows exceptions to bubble up
        if 'code = 1000 (OK)' in s:
            return errors.WebSocketDisconnected(WSCloseCode.NORMAL)

        # NOTE(kgriffs): Autobahn (used by Daphne) raises a generic exception
        #   with this message
        if 'protocol accepted must be from the list' in s:
            return ValueError(
                'WebSocket subprotocol must be from the list sent by the client'
            )

        # NOTE(vytas): Per ASGI HTTP & WebSocket spec v2.4:
        #   If send() is called on a closed connection the server should raise
        #   a server-specific subclass of IOError.
        # NOTE(vytas): Uvicorn 0.30.6 seems to conform to the spec only when
        #   using the wsproto stack, it then raises an instance of
        #   uvicorn.protocols.utils.ClientDisconnected.
        if isinstance(ex, OSError):
            close_code = None

            # NOTE(vytas): If using the "websockets" backend, Uvicorn raises
            #   and instance of OSError from a websockets exception like this:
            #   "received 1001 (going away); then sent 1001 (going away)"
            if ex.__cause__:
                match = _CLIENT_DISCONNECTED_CAUSE.match(str(ex.__cause__))
                if match:
                    close_code = int(match.group(1))

            return errors.WebSocketDisconnected(close_code)

        return None


class WebSocketOptions:
    """Defines a set of configurable WebSocket options.

    An instance of this class is exposed via :attr:`falcon.asgi.App.ws_options`
    for configuring certain :class:`~.WebSocket` behaviors.
    """

    error_close_code: int
    """The WebSocket close code to use when an unhandled error is raised while
    handling a WebSocket connection (default ``1011``).

    For a list of valid close codes and ranges, see also:
    https://tools.ietf.org/html/rfc6455#section-7.4.
    """
    default_close_reasons: Dict[int, str]
    """A default mapping between the Websocket close code, and the reason why
    the connection is closed.
    Close codes corresponding to HTTP errors are also included in this mapping.
    """
    media_handlers: Dict[
        WebSocketPayloadType, Union[media.TextBaseHandlerWS, media.BinaryBaseHandlerWS]
    ]
    """A dict-like object for configuring media handlers according to the WebSocket
    payload type (TEXT vs. BINARY) of a given message.

    See also: :ref:`ws_media_handlers`.
    """
    max_receive_queue: int
    """The maximum number of incoming messages to enqueue if the reception rate
    exceeds the consumption rate of the application (default ``4``).

    When this limit is reached, the framework will wait to accept new messages
    from the ASGI server until the application is able to catch up.

    This limit applies to Falcon's incoming message queue, and should
    generally be kept small since the ASGI server maintains its
    own receive queue. Falcon's queue can be disabled altogether by
    setting `max_receive_queue` to ``0`` (see also: :ref:`ws_lost_connection`).
    """

    __slots__ = [
        'error_close_code',
        'default_close_reasons',
        'max_receive_queue',
        'media_handlers',
    ]

    _STANDARD_CLOSE_REASONS = (
        (1000, 'Normal Closure'),
        (1011, 'Internal Server Error'),
        (3011, 'Internal Server Error'),
    )

    @classmethod
    def _init_default_close_reasons(cls) -> Dict[int, str]:
        reasons = dict(cls._STANDARD_CLOSE_REASONS)
        for status_constant in dir(status_codes):
            if 'HTTP_100' <= status_constant < 'HTTP_599':
                status_line = getattr(status_codes, status_constant)
                status_code, _, phrase = status_line.partition(' ')
                reasons[http_status_to_ws_code(int(status_code))] = phrase
        return reasons

    def __init__(self) -> None:
        try:
            import msgpack
        except ImportError:
            msgpack = None

        bin_handler: media.BinaryBaseHandlerWS

        if msgpack:
            bin_handler = media.MessagePackHandlerWS()
        else:
            bin_handler = media.MissingDependencyHandler(
                'default WebSocket media handler for BINARY payloads', 'msgpack'
            )

        self.media_handlers = {
            WebSocketPayloadType.TEXT: media.JSONHandlerWS(),
            WebSocketPayloadType.BINARY: bin_handler,
        }

        # Internal Error
        #
        #   See also: https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent
        #
        self.error_close_code = WSCloseCode.SERVER_ERROR
        self.default_close_reasons = self._init_default_close_reasons()

        # NOTE(kgriffs): The websockets library itself will buffer, so we keep
        #   this value fairly small by default to mitigate buffer bloat. But in
        #   the case that we have a large spillover from the websocket server's
        #   own queue, increasing the queue length on our side may reduce the
        #   number of pauses in the pump task as it drains the message
        #   backlog. Whether or not this hypothetical will have a material
        #   real-world impact remains to be seen.
        #
        #   See also:
        #       * https://websockets.readthedocs.io/en/stable/design.html#buffers
        #       * https://websockets.readthedocs.io/en/stable/deployment.html#buffers
        #
        self.max_receive_queue = 4


class _BufferedReceiver:
    """Buffer incoming WebSocket messages.

    This class is used internally to monitor the WebSocket status (so that we
    can detect when it is disconnected).
    """

    __slots__ = [
        '_asgi_receive',
        '_loop',
        '_max_queue',
        '_messages',
        '_pop_message_waiter',
        '_pump_task',
        '_put_message_waiter',
        'client_disconnected',
        'client_disconnected_code',
    ]

    _pop_message_waiter: Optional[asyncio.Future[None]]
    _put_message_waiter: Optional[asyncio.Future[None]]
    _pump_task: Optional[asyncio.Task[None]]
    _messages: Deque[AsgiEvent]
    client_disconnected: bool
    client_disconnected_code: Optional[int]

    def __init__(self, asgi_receive: AsgiReceive, max_queue: int) -> None:
        self._asgi_receive = asgi_receive
        self._max_queue = max_queue

        self._loop = asyncio.get_running_loop()

        self._messages = collections.deque()
        self._pop_message_waiter = None
        self._put_message_waiter = None

        self._pump_task = None

        self.client_disconnected = False
        self.client_disconnected_code = None

    def start(self) -> None:
        # NOTE(vytas): Do not start anything if buffering is disabled.
        if self._pump_task is None and self._max_queue > 0:
            self._pump_task = asyncio.create_task(self._pump())

    async def stop(self) -> None:
        if self._pump_task is None:
            return

        self._pump_task.cancel()
        try:
            await self._pump_task
        except asyncio.CancelledError:
            pass

        self._pump_task = None

    async def receive(self) -> AsgiEvent:
        # NOTE(kgriffs): Since this class is only used internally, we
        #   use an assertion to mitigate against framework bugs.
        #
        #   receive() may not be called again while another coroutine
        #   is already waiting for the next message.
        assert self._pop_message_waiter is None
        assert self._pump_task is not None

        # NOTE(kgriffs): Wait for a message if none are available. This pattern
        #   was borrowed from the websockets.protocol module.
        while not self._messages:
            # --------------------------------------------------------------------------
            # NOTE(kgriffs): The pattern below was borrowed from the websockets.protocol
            #   module under the BSD 3-Clause "New" or "Revised" License.
            #
            #   Ref: https://github.com/aaugustin/websockets/blob/master/src/websockets/protocol.py  # noqa E501
            #
            # --------------------------------------------------------------------------

            # PERF(kgriffs): Using a bare future like this seems to be
            #   slightly more efficient vs. something like asyncio.Event
            pop_message_waiter = self._loop.create_future()
            self._pop_message_waiter = pop_message_waiter

            try:
                await asyncio.wait(
                    [pop_message_waiter, self._pump_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
            finally:
                self._pop_message_waiter = None

            if not pop_message_waiter.done():
                # NOTE(kgriffs): asyncio.wait(...) exited because
                #   self._pump_task completed before receiving a
                #   new message.
                pop_message_waiter.cancel()
                return {
                    'type': EventType.WS_DISCONNECT,
                }

        message = self._messages.popleft()

        # Notify _pump()
        if self._put_message_waiter is not None:
            self._put_message_waiter.set_result(None)
            self._put_message_waiter = None

        return message

    async def _pump(self) -> None:
        while not self.client_disconnected:
            received_event = await self._asgi_receive()
            if received_event['type'] == EventType.WS_DISCONNECT:
                self.client_disconnected = True
                self.client_disconnected_code = received_event.get(
                    'code', WSCloseCode.NORMAL
                )

            # --------------------------------------------------------------------------
            # NOTE(kgriffs): The pattern below was borrowed from the websockets.protocol
            #   module under the BSD 3-Clause "New" or "Revised" License.
            #
            #   Ref: https://github.com/aaugustin/websockets/blob/master/src/websockets/protocol.py # noqa E501
            #
            # --------------------------------------------------------------------------
            while len(self._messages) >= self._max_queue:
                self._put_message_waiter = self._loop.create_future()
                try:
                    await self._put_message_waiter
                finally:
                    self._put_message_waiter = None

            self._messages.append(received_event)

            # Notify receive()
            if self._pop_message_waiter is not None:
                self._pop_message_waiter.set_result(None)
                self._pop_message_waiter = None


@misc._lru_cache_for_simple_logic(maxsize=16)
def _supports_reason(asgi_ver: str) -> bool:
    """Check if the websocket version support a close reason."""
    target_ver = (2, 3)
    current_ver = tuple(map(int, asgi_ver.split('.')))
    return current_ver >= target_ver


def http_status_to_ws_code(http_status: int) -> int:
    """Convert the provided http status to a websocket close code by adding 3000."""
    return http_status + 3000
