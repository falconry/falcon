from __future__ import annotations

import json

import falcon
from falcon.typing import ReadableIO


class CustomJSONHandler(falcon.media.BaseHandler):
    MAX_INDENT_LEVEL = 8

    def deserialize(
        self,
        stream: ReadableIO,
        content_type: str | None,
        content_length: int | None,
    ) -> object:
        data = stream.read()
        return json.loads(data.decode())

    def serialize(self, media: object, content_type: str) -> bytes:
        _, params = falcon.parse_header(content_type)
        indent_param = params.get('indent')
        indent: int | None = None
        if indent_param is not None:
            try:
                indent = int(indent_param)
                # NOTE: Impose a reasonable indentation level limit.
                if indent < 0 or indent > self.MAX_INDENT_LEVEL:
                    indent = None
            except ValueError:
                # TODO: Handle invalid params?
                indent = None

        result = json.dumps(media, indent=indent, sort_keys=bool(indent))
        return result.encode()
