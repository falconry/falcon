import copy
import mimetypes
import os.path

import falcon


class StaticSink:

    _additional_types = {
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.html': 'text/html',
        '.svg': 'image/svg+xml',

        '.png': 'image/png',
        '.jpeg': 'image/jpeg',
        '.jp2': 'image/jpeg',
        '.gif': 'image/gif',
        '.tiff': 'image/tiff',
    }

    def __init__(self, prefix, parent_folder):
        self.prefix = prefix
        self.parent_folder = os.path.abspath(parent_folder)
        self.mime_types = copy.copy(mimetypes.encodings_map)

        self.mime_types.update(self._additional_types)

    def __call__(self, req, resp):
        stripped = req.path.replace(self.prefix, '')
        cleaned = stripped.replace('../', '').lstrip('/')
        path = os.path.join(self.parent_folder, cleaned)
        suffix = os.path.splitext(path)[1]

        try:
            resp.stream = open(path, 'rb')
        except IOError:
            raise falcon.HTTPNotFound()

        resp.content_type = self.mime_types.get(suffix, 'application/octet-stream')

        raise falcon.HTTPStatus('200 OK')
