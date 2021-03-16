import hashlib
import io
import os.path

import falcon


HERE = os.path.abspath(os.path.dirname(__file__))


class Forms:
    def on_post(self, req, resp):
        parts = {}

        for part in req.media:
            # NOTE(vytas): SHA1 is no longer recommended for cryptographic
            #   purposes, but here we are only using it for integrity checking.
            sha1 = hashlib.sha1()
            while True:
                chunk = part.stream.read(io.DEFAULT_BUFFER_SIZE)
                if not chunk:
                    break

                sha1.update(chunk)

            parts[part.name] = {
                'filename': part.filename,
                'sha1': sha1.hexdigest(),
            }

        resp.media = parts


class Hello:
    def on_get(self, req, resp):
        resp.set_header('X-Falcon', 'peregrine')

        resp.content_type = falcon.MEDIA_TEXT
        resp.text = 'Hello, World!\n'

    def on_get_deprecated(self, req, resp):
        resp.set_header('X-Falcon', 'deprecated')

        resp.content_type = falcon.MEDIA_TEXT
        resp.body = 'Hello, World!\n'


app = application = falcon.App()
app.add_route('/forms', Forms())
app.add_route('/hello', Hello())
app.add_route('/deprecated', Hello(), suffix='deprecated')
app.add_static_route('/tests', HERE, downloadable=True)
