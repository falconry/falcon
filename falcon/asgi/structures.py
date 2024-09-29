from __future__ import annotations

from typing import Optional

from falcon.constants import MEDIA_JSON
from falcon.media import BaseHandler
from falcon.media.json import _DEFAULT_JSON_HANDLER

__all__ = ('SSEvent',)


class SSEvent:
    """Represents a Server-Sent Event (SSE).

    Instances of this class can be yielded by an async generator in order to
    send a series of `Server-Sent Events`_ to the user agent.

    (See also: :attr:`falcon.asgi.Response.sse`)

    Keyword Args:
        data (bytes): Raw byte string to use as the ``data`` field for the
            event message. Takes precedence over both `text` and `json`.
        text (str): String to use for the ``data`` field in the message. Will
            be encoded as UTF-8 in the event. Takes precedence over `json`.
        json (object): JSON-serializable object to be converted to JSON and
            used as the ``data`` field in the event message.
        event (str): A string identifying the event type (AKA event name).
        event_id (str): The event ID that the User Agent should use for
            the `EventSource` object's last event ID value.
        retry (int): The reconnection time to use when attempting to send the
            event. This must be an integer, specifying the reconnection time
            in milliseconds.
        comment (str): Comment to include in the event message; this is
            normally ignored by the user agent, but is useful when composing
            a periodic "ping" message to keep the connection alive. Since this
            is a common use case, a default "ping" comment will be included
            in any event that would otherwise be blank (i.e., one that does
            not specify any fields when initializing the `SSEvent` instance.)

    .. _Server-Sent Events:
        https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
    """

    __slots__ = [
        'data',
        'text',
        'json',
        'event',
        'event_id',
        'retry',
        'comment',
    ]

    data: Optional[bytes]
    """Raw byte string to use as the ``data`` field for the event message.
    Takes precedence over both `text` and `json`.
    """
    text: Optional[str]
    """String to use for the ``data`` field in the message.
    Will be encoded as UTF-8 in the event. Takes precedence over `json`.
    """
    json: object
    """JSON-serializable object to be converted to JSON and used as the ``data``
    field in the event message.
    """
    event: Optional[str]
    """A string identifying the event type (AKA event name)."""
    event_id: Optional[str]
    """The event ID that the User Agent should use for the `EventSource` object's
    last event ID value.
    """
    retry: Optional[int]
    """The reconnection time to use when attempting to send the event.

    This must be an integer, specifying the reconnection time in milliseconds.
    """
    comment: Optional[str]
    """Comment to include in the event message.

    This is normally ignored by the user agent, but is useful when composing a periodic
    "ping" message to keep the connection alive. Since this is a common use case, a
    default "ping" comment will be included in any event that would otherwise be blank
    (i.e., one that does not specify any of the fields when initializing the
    :class:`SSEvent` instance.)
    """

    def __init__(
        self,
        data: Optional[bytes] = None,
        text: Optional[str] = None,
        json: Optional[object] = None,
        event: Optional[str] = None,
        event_id: Optional[str] = None,
        retry: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> None:
        # NOTE(kgriffs): Check up front since this makes it a lot easier
        #   to debug the source of the problem in the app vs. waiting for
        #   an error to be raised from the framework when it calls serialize()
        #   after the fact.

        if data is not None and not isinstance(data, bytes):
            raise TypeError('data must be a byte string')

        if text is not None and not isinstance(text, str):
            raise TypeError('text must be a string')

        if event is not None and not isinstance(event, str):
            raise TypeError('event name must be a string')

        if event_id is not None and not isinstance(event_id, str):
            raise TypeError('event_id must be a string')

        if comment is not None and not isinstance(comment, str):
            raise TypeError('comment must be a string')

        if retry is not None and not isinstance(retry, int):
            raise TypeError('retry must be an int')

        self.data = data
        self.text = text
        self.json = json
        self.event = event
        self.event_id = event_id
        self.retry = retry

        self.comment = comment

    def serialize(self, handler: Optional[BaseHandler] = None) -> bytes:
        """Serialize this event to string.

        Args:
            handler: Handler object that will be used to serialize the ``json``
                attribute to string. When not provided, a default handler using
                the builtin JSON library will be used (default ``None``).

        Returns:
            bytes: string representation of this event.
        """
        if self.comment is not None:
            block = f': {self.comment}\n'
        else:
            block = ''

        if self.event is not None:
            block += f'event: {self.event}\n'

        if self.event_id is not None:
            # NOTE(kgriffs): f-strings are a tiny bit faster than str().
            block += f'id: {self.event_id}\n'

        if self.retry is not None:
            block += f'retry: {self.retry}\n'

        if self.data is not None:
            # NOTE(kgriffs): While this decode() may seem unnecessary, it
            #   does provide a check to ensure it is valid UTF-8. I'm also
            #   assuming for the moment that most people will not use this
            #   attribute, but rather the text and json ones instead. If that
            #   is true, it makes sense to construct the entire string
            #   first, then encode it all in one go at the end.
            block += f'data: {self.data.decode()}\n'
        elif self.text is not None:
            block += f'data: {self.text}\n'
        elif self.json is not None:
            if handler is None:
                handler = _DEFAULT_JSON_HANDLER
            serialized = handler.serialize(self.json, MEDIA_JSON)
            block += 'data: '
            return block.encode() + serialized + b'\n\n'

        if not block:
            return b': ping\n\n'

        return (block + '\n').encode()
