from __future__ import absolute_import

from falcon import errors
from falcon.media import BaseHandler
from falcon.util import compat
from falcon.util import json


class JSONHandler(BaseHandler):
    """JSON media handler.

    This handler uses Python's :py:mod:`json` by default, but will
    use :py:mod:`ujson` if available.

    Keyword Arguments:
        dumps (func): the function to use when serializing JSON responses

        loads (func): the function to use when deserializing JSON requests

        dumps_kwargs (dict): keyword arguments passed to ``dumps`` when serializing to JSON.
            ``ensure_ascii`` is set to ``false`` by default. To override this setting, pass ``True``
            explicitly.

        loads_kwargs (func): keyword arguments to pass to ``loads`` when deserializing from JSON.


    You can override the JSON library used by changing the ``dumps`` and ``loads`` functions::

        import falcon
        from falcon import media
        import rapidjson


        json_handler = media.JSONHandler(
            dumps=rapidjson.dumps,
            loads=rapidjson.loads,
            dumps_kwargs=dict(ensure_ascii=False)
        )
        extra_handlers = {
            'application/json': json_handler,
            'application/json; charset=UTF-8': json_handler,
        }

        api = falcon.API()
        api.req_options.media_handlers.update(extra_handlers)
        api.resp_options.media_handlers.update(extra_handlers)
    """

    def __init__(self, dumps=None, dumps_kwargs=None, loads=None, loads_kwargs=None):
        self.dumps = dumps or json.dumps
        self.dumps_kwargs = dict(ensure_ascii=False)
        self.dumps_kwargs.update(dumps_kwargs or dict())

        self.loads = loads or json.loads
        self.loads_kwargs = dict()
        self.loads_kwargs.update(loads_kwargs or dict())

    def deserialize(self, stream, content_type, content_length):
        try:
            return self.loads(stream.read().decode('utf-8'), **self.loads_kwargs)
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid JSON',
                'Could not parse JSON body - {0}'.format(err)
            )

    def serialize(self, media, content_type):
        result = self.dumps(media, **self.dumps_kwargs)

        if compat.PY3 or not isinstance(result, bytes):
            return result.encode('utf-8')

        return result
