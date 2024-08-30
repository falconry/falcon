from __future__ import annotations

from functools import partial
import json
from typing import Any, Callable, Optional, Union

from falcon import errors
from falcon import http_error
from falcon.media.base import BaseHandler
from falcon.media.base import TextBaseHandlerWS
from falcon.typing import AsyncReadableIO
from falcon.typing import ReadableIO


class JSONHandler(BaseHandler):
    """JSON media handler.

    This handler uses Python's standard :mod:`json` library by default, but
    can be easily configured to use any of a number of third-party JSON
    libraries, depending on your needs. For example, you can often
    realize a significant performance boost under CPython by using an
    alternative library. Good options in this respect include `orjson`,
    `python-rapidjson`, and `mujson`.

    This handler will raise a :class:`falcon.MediaNotFoundError` when attempting
    to parse an empty body, or a :class:`falcon.MediaMalformedError`
    if an error happens while parsing the body.

    Note:
        If you are deploying to PyPy, we recommend sticking with the standard
        library's JSON implementation, since it will be faster in most cases
        as compared to a third-party library.

    .. rubric:: Custom JSON library

    You can replace the default JSON handler by using a custom JSON library
    (see also: :ref:`custom_media_handlers`). Overriding the default JSON
    implementation is simply a matter of specifying the desired ``dumps`` and
    ``loads`` functions::

        import falcon
        from falcon import media

        import rapidjson

        json_handler = media.JSONHandler(
            dumps=rapidjson.dumps,
            loads=rapidjson.loads,
        )
        extra_handlers = {
            'application/json': json_handler,
        }

        app = falcon.App()
        app.req_options.media_handlers.update(extra_handlers)
        app.resp_options.media_handlers.update(extra_handlers)

    .. rubric:: Custom serialization parameters

    Even if you decide to stick with the stdlib's :any:`json.dumps` and
    :any:`json.loads`, you can wrap them using :any:`functools.partial` to
    provide custom serialization or deserialization parameters supported by the
    ``dumps`` and ``loads`` functions, respectively
    (see also: :ref:`prettifying-json-responses`)::

        import falcon
        from falcon import media

        from functools import partial

        json_handler = media.JSONHandler(
            dumps=partial(
                json.dumps,
                default=str,
                sort_keys=True,
            ),
        )
        extra_handlers = {
            'application/json': json_handler,
        }

        app = falcon.App()
        app.req_options.media_handlers.update(extra_handlers)
        app.resp_options.media_handlers.update(extra_handlers)

    By default, ``ensure_ascii`` is passed to the ``json.dumps`` function.
    If you override the ``dumps`` function, you will need to explicitly set
    ``ensure_ascii`` to ``False`` in order to enable the serialization of
    Unicode characters to UTF-8. This is easily done by using
    :any:`functools.partial` to apply the desired keyword argument. As also
    demonstrated in the previous paragraph, you can use this same technique to
    customize any option supported by the ``dumps`` and ``loads`` functions::

        from functools import partial

        from falcon import media
        import rapidjson

        json_handler = media.JSONHandler(
            dumps=partial(
                rapidjson.dumps,
                ensure_ascii=False, sort_keys=True
            ),
        )

    .. _custom-media-json-encoder:

    .. rubric:: Custom JSON encoder

    You can also override the default :class:`~json.JSONEncoder` by using a
    custom Encoder and updating the media handlers for ``application/json``
    type to use that::

        import json
        from datetime import datetime
        from functools import partial

        import falcon
        from falcon import media

        class DatetimeEncoder(json.JSONEncoder):
            \"\"\"Json Encoder that supports datetime objects.\"\"\"

            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)

        app = falcon.App()

        json_handler = media.JSONHandler(
            dumps=partial(json.dumps, cls=DatetimeEncoder),
        )
        extra_handlers = {
            'application/json': json_handler,
        }

        app.req_options.media_handlers.update(extra_handlers)
        app.resp_options.media_handlers.update(extra_handlers)

    .. note:: When testing an application employing a custom JSON encoder, bear
        in mind that :class:`~.testing.TestClient` is decoupled from the app,
        and it simulates requests as if they were performed by a third-party
        client (just sans network). Therefore, passing the **json** parameter
        to :ref:`simulate_* <testing_standalone_methods>` methods will
        effectively use the stdlib's :func:`json.dumps`. If you want to
        serialize custom objects for testing, you will need to dump them into a
        string yourself, and pass it using the **body** parameter instead
        (accompanied by the ``application/json`` content type header).

    Keyword Arguments:
        dumps (func): Function to use when serializing JSON responses.
        loads (func): Function to use when deserializing JSON requests.
    """

    def __init__(
        self,
        dumps: Optional[Callable[[Any], Union[str, bytes]]] = None,
        loads: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self._dumps = dumps or partial(json.dumps, ensure_ascii=False)
        self._loads = loads or json.loads

        # PERF(kgriffs): Test dumps once up front so we can set the
        #     proper serialize implementation.
        result = self._dumps({'message': 'Hello World'})
        if isinstance(result, str):
            self.serialize = self._serialize_s  # type: ignore[method-assign]
            self.serialize_async = self._serialize_async_s  # type: ignore[method-assign]
        else:
            self.serialize = self._serialize_b  # type: ignore[method-assign]
            self.serialize_async = self._serialize_async_b  # type: ignore[method-assign]

        # NOTE(kgriffs): To be safe, only enable the optimized protocol when
        #   not subclassed.
        if type(self) is JSONHandler:
            self._serialize_sync = self.serialize
            self._deserialize_sync = self._deserialize

    def _deserialize(self, data: bytes) -> Any:
        if not data:
            raise errors.MediaNotFoundError('JSON')
        try:
            return self._loads(data.decode())
        except ValueError as err:
            raise errors.MediaMalformedError('JSON') from err

    def deserialize(
        self,
        stream: ReadableIO,
        content_type: Optional[str],
        content_length: Optional[int],
    ) -> Any:
        return self._deserialize(stream.read())

    async def deserialize_async(
        self,
        stream: AsyncReadableIO,
        content_type: Optional[str],
        content_length: Optional[int],
    ) -> Any:
        return self._deserialize(await stream.read())

    # NOTE(kgriffs): Make content_type a kwarg to support the
    #   Request.render_body() shortcut optimization.
    def _serialize_s(self, media: Any, content_type: Optional[str] = None) -> bytes:
        return self._dumps(media).encode()  # type: ignore[union-attr]

    async def _serialize_async_s(
        self, media: Any, content_type: Optional[str]
    ) -> bytes:
        return self._dumps(media).encode()  # type: ignore[union-attr]

    # NOTE(kgriffs): Make content_type a kwarg to support the
    #   Request.render_body() shortcut optimization.
    def _serialize_b(self, media: Any, content_type: Optional[str] = None) -> bytes:
        return self._dumps(media)  # type: ignore[return-value]

    async def _serialize_async_b(
        self, media: Any, content_type: Optional[str]
    ) -> bytes:
        return self._dumps(media)  # type: ignore[return-value]


class JSONHandlerWS(TextBaseHandlerWS):
    """WebSocket media handler for de(serializing) JSON to/from TEXT payloads.

    This handler uses Python's standard :mod:`json` library by default, but
    can be easily configured to use any of a number of third-party JSON
    libraries, depending on your needs. For example, you can often
    realize a significant performance boost under CPython by using an
    alternative library. Good options in this respect include `orjson`,
    `python-rapidjson`, and `mujson`.

    Note:
        If you are deploying to PyPy, we recommend sticking with the standard
        library's JSON implementation, since it will be faster in most cases
        as compared to a third-party library.

    Overriding the default JSON implementation is simply a matter of specifying
    the desired ``dumps`` and ``loads`` functions::

        import falcon
        from falcon import media

        import rapidjson

        json_handler = media.JSONHandlerWS(
            dumps=rapidjson.dumps,
            loads=rapidjson.loads,
        )

        app = falcon.asgi.App()
        app.ws_options.media_handlers[falcon.WebSocketPayloadType.TEXT] = json_handler

    By default, ``ensure_ascii`` is passed to the ``json.dumps`` function.
    If you override the ``dumps`` function, you will need to explicitly set
    ``ensure_ascii`` to ``False`` in order to enable the serialization of
    Unicode characters to UTF-8. This is easily done by using
    :any:`functools.partial` to apply the desired keyword argument. In fact, you
    can use this same technique to customize any option supported by the
    ``dumps`` and ``loads`` functions::

        from functools import partial

        from falcon import media
        import rapidjson

        json_handler = media.JSONHandlerWS(
            dumps=partial(
                rapidjson.dumps,
                ensure_ascii=False, sort_keys=True
            ),
        )

    Keyword Arguments:
        dumps (func): Function to use when serializing JSON.
        loads (func): Function to use when deserializing JSON.
    """

    __slots__ = ['dumps', 'loads']

    def __init__(
        self,
        dumps: Optional[Callable[[Any], str]] = None,
        loads: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self._dumps = dumps or partial(json.dumps, ensure_ascii=False)
        self._loads = loads or json.loads

    def serialize(self, media: object) -> str:
        return self._dumps(media)

    def deserialize(self, payload: str) -> object:
        return self._loads(payload)


http_error._DEFAULT_JSON_HANDLER = _DEFAULT_JSON_HANDLER = JSONHandler()
