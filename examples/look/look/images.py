import io
import json
import mimetypes
import os
import re
import uuid

import falcon


class Collection:
    def __init__(self, image_store):
        self._image_store = image_store

    def on_get(self, req, resp):
        max_size = req.get_param_as_int('maxsize', min_value=1, default=-1)
        images = self._image_store.list(max_size)
        doc = {'images': [{'href': '/images/' + image} for image in images]}

        resp.text = json.dumps(doc, ensure_ascii=False)
        resp.status = falcon.HTTP_200

    def on_post(self, req, resp):
        name = self._image_store.save(req.stream, req.content_type)
        resp.status = falcon.HTTP_201
        resp.location = '/images/' + name


class Item:
    def __init__(self, image_store):
        self._image_store = image_store

    def on_get(self, req, resp, name):
        resp.content_type = mimetypes.guess_type(name)[0]
        resp.stream, resp.content_length = self._image_store.open(name)


class ImageStore:
    _CHUNK_SIZE_BYTES = 4096
    _IMAGE_NAME_PATTERN = re.compile(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.[a-z]{2,4}$'
    )

    # Note the use of dependency injection for standard library
    # methods. We'll use these later to avoid monkey-patching.
    def __init__(self, storage_path, uuidgen=uuid.uuid4, fopen=io.open):
        self._storage_path = storage_path
        self._uuidgen = uuidgen
        self._fopen = fopen

    def save(self, image_stream, image_content_type):
        ext = mimetypes.guess_extension(image_content_type)
        name = '{uuid}{ext}'.format(uuid=self._uuidgen(), ext=ext)
        image_path = os.path.join(self._storage_path, name)

        with self._fopen(image_path, 'wb') as image_file:
            while True:
                chunk = image_stream.read(self._CHUNK_SIZE_BYTES)
                if not chunk:
                    break

                image_file.write(chunk)

        return name

    def open(self, name):
        # Always validate untrusted input!
        if not self._IMAGE_NAME_PATTERN.match(name):
            raise IOError('File not found')

        image_path = os.path.join(self._storage_path, name)
        stream = self._fopen(image_path, 'rb')
        content_length = os.path.getsize(image_path)

        return stream, content_length

    def list(self, max_size):
        images = [
            image
            for image in os.listdir(self._storage_path)
            if self._IMAGE_NAME_PATTERN.match(image)
            and (
                max_size == -1
                or os.path.getsize(os.path.join(self._storage_path, image)) <= max_size
            )
        ]
        return images
