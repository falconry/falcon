import os.path
import falcon


class Statics:

    def __init__(self, prefix, parent_folder):
        self.prefix = prefix
        self.parent_folder = os.path.abspath(parent_folder)


    def _get_stream(self, path):
        with open(path, 'rb') as f:
            return f

    def __call__(self, req, resp):
        stripped = req.path[len(self.prefix):]
        normalized = os.path.normpath(stripped).lstrip('/')

        if normalized.startswith('../'):
            raise falcon.HTTPNotFound()

        path = os.path.join(self.parent_folder, normalized)

        try:
            resp.stream = self._get_stream(path)
        except IOError:
            raise falcon.HTTPNotFound()

        suffix = os.path.splitext(path)[1]
        resp.content_type = resp.options.static_media_types.get(suffix, 'application/octet-stream')
