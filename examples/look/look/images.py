import mimetypes
import os
import uuid

import msgpack

import falcon


class Resource(object):

    def __init__(self, image_saver):
        self.image_saver = image_saver

    def on_get(self, req, resp):
        resp.data = msgpack.packb({'message': 'Hello world!'})
        resp.content_type = 'application/msgpack'
        resp.status = falcon.HTTP_200

    def on_post(self, req, resp):
        filename = self.image_saver.save(req.stream, req.content_type)
        resp.status = falcon.HTTP_201
        resp.location = '/images/' + filename


class ImageSaver:

    def __init__(self, storage_path):
        self.storage_path = storage_path

    def save(self, image_stream, image_content_type):
        ext = mimetypes.guess_extension(image_content_type)
        filename = '{uuid}{ext}'.format(uuid=uuid.uuid4(), ext=ext)
        image_path = os.path.join(self.storage_path, filename)

        with open(image_path, 'wb') as image_file:
            while True:
                chunk = image_stream.read(4096)
                if not chunk:
                    break

                image_file.write(chunk)
        return filename
