from functools import partial
import json

from falcon import errors
from falcon import http_error
from falcon.media.base import BaseHandler, TextBaseHandlerWS


class JSONHandler(BaseHandler):
    """JSON media handler.

    This handler uses Python's standard :py:mod:`json` library by default, but
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

        json_handler = media.JSONHandler(
            dumps=partial(
                rapidjson.dumps,
                ensure_ascii=False, sort_keys=True
            ),
        )

    Keyword Arguments:
        dumps (func): Function to use when serializing JSON responses.
        loads (func): Function to use when deserializing JSON requests.
    """

    def __init__(self, dumps=None, loads=None):
        self.dumps = dumps or partial(json.dumps, ensure_ascii=False)
        self.loads = loads or json.loads

        # PERF(kgriffs): Test dumps once up front so we can set the
        #     proper serialize implementation.
        result = self.dumps({'message': 'Hello World'})
        if isinstance(result, str):
            self.serialize = self._serialize_s
            self.serialize_async = self._serialize_async_s
        else:
            self.serialize = self._serialize_b
            self.serialize_async = self._serialize_async_b

    def deserialize(self, stream, content_type, content_length):
        try:
            return self.loads(stream.read().decode())
        except ValueError as err:
            raise errors.HTTPBadRequest(
                title='Invalid JSON',
                description='Could not parse JSON - {0}'.format(err)
            )

    async def deserialize_async(self, stream, content_type, content_length):
        data = await stream.read()

        try:
            return self.loads(data.decode())
        except ValueError as err:
            raise errors.HTTPBadRequest(
                title='Invalid JSON',
                description='Could not parse JSON - {0}'.format(err)
            )

    def _serialize_s(self, media, content_type):
        return self.dumps(media).encode()

    async def _serialize_async_s(self, media, content_type):
        return self.dumps(media).encode()

    def _serialize_b(self, media, content_type):
        return self.dumps(media)

    async def _serialize_async_b(self, media, content_type):
        return self.dumps(media)


class JSONHandlerWS(TextBaseHandlerWS):
    """WebSocket media handler for de(serializing) JSON to/from TEXT payloads.

    This handler uses Python's standard :py:mod:`json` library by default, but
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

    def __init__(self, dumps=None, loads=None):
        self.dumps = dumps or partial(json.dumps, ensure_ascii=False)
        self.loads = loads or json.loads

    def serialize(self, media: object) -> str:
        return self.dumps(media)

    def deserialize(self, payload: str) -> object:
        return self.loads(payload)


http_error._DEFAULT_JSON_HANDLER = _DEFAULT_JSON_HANDLER = JSONHandler()  # type: ignore
