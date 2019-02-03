from __future__ import absolute_import

from functools import partial

from falcon import errors
from falcon.media import BaseHandler
from falcon.util import json


class JSONHandler(BaseHandler):
    """JSON media handler.

    This handler uses Python's :py:mod:`json` by default, but will
    use :py:mod:`ujson` if available.

    Keyword Arguments:
        dumps (func): the function to use when serializing JSON responses.
        loads (func): the function to use when deserializing JSON requests.

    You can override the JSON library used by changing the ``dumps`` and
    ``loads`` functions. Some good options are orjson, python-rapidjson,
    and mujson.::

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

        api = falcon.API()
        api.req_options.media_handlers.update(extra_handlers)
        api.resp_options.media_handlers.update(extra_handlers)

    By default, ``ensure_ascii`` is passed to the ``json.dumps`` function.
    If you override the ``dumps`` function, you will need to explicitly set
    ``ensure_ascii`` to ``False`` in order to enable the serialization of
    Unicode characters to UTF-8. This is easily done by using
    ``functools.partial`` to curry the keyword arguments. This gives you
    complete control over the behavior of the ``dumps`` and ``loads``
    functions.

    ::

        from functools import partial
        import ujson

        json_handler = media.JSONHandler(
            dumps=partial(
                ujson.dumps,
                ensure_ascii=False, escape_forward_slashes=True
            ),
        )
    """

    def __init__(self, dumps=None, loads=None):
        self.dumps = dumps or partial(json.dumps, ensure_ascii=False)
        self.loads = loads or json.loads

    def deserialize(self, stream, content_type, content_length):
        try:
            return self.loads(stream.read().decode('utf-8'))
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid JSON',
                'Could not parse JSON body - {0}'.format(err)
            )

    def serialize(self, media, content_type):
        result = self.dumps(media)

        if not isinstance(result, bytes):
            return result.encode('utf-8')

        return result
