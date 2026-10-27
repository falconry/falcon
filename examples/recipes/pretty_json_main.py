import json
from typing import Any, IO, Optional

import falcon


class CustomJSONHandler(falcon.media.BaseHandler):
    MAX_INDENT_LEVEL = 8

    def deserialize(
        self, stream: IO[bytes], content_type: str, content_length: int
    ) -> Any:
        data = stream.read()
        return json.loads(data.decode())

    def serialize(self, media: Any, content_type: str) -> bytes:
        _, params = falcon.parse_header(content_type)
        indent: Optional[int] = params.get('indent')
        if indent is not None:
            try:
                indent = int(indent)
                # NOTE: Impose a reasonable indentation level limit.
                if indent < 0 or indent > self.MAX_INDENT_LEVEL:
                    indent = None
            except ValueError:
                # TODO: Handle invalid params?
                indent = None

        result = json.dumps(media, indent=indent, sort_keys=bool(indent))
        return result.encode()
