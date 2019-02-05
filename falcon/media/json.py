from __future__ import absolute_import

from functools import partial

from falcon import errors
from falcon.media import BaseHandler
from falcon.util import json


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

        api = falcon.API()
        api.req_options.media_handlers.update(extra_handlers)
        api.resp_options.media_handlers.update(extra_handlers)

    By default, ``ensure_ascii`` is passed to the ``json.dumps`` function.
    If you override the ``dumps`` function, you will need to explicitly set
    ``ensure_ascii`` to ``False`` in order to enable the serialization of
    Unicode characters to UTF-8. This is easily done by using
    ``functools.partial`` to apply the desired keyword argument. In fact, you
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
