import json

import falcon


class CustomJSONHandler(falcon.media.BaseHandler):
    MAX_INDENT_LEVEL = 8

    def deserialize(self, stream, content_type, content_length):
        data = stream.read()
        return json.loads(data.decode())

    def serialize(self, media, content_type):
        _, params = falcon.parse_header(content_type)
        indent = params.get('indent')
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
