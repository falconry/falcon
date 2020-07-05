import asyncio
import datetime
import io
import os.path

import aiofiles
import falcon
import PIL.Image


class Image:

    def __init__(self, config, image_id, size):
        self.config = config
        self.image_id = image_id
        self.size = size
        self.modified = datetime.datetime.utcnow()

    @property
    def path(self):
        return os.path.join(self.config.storage_path, self.image_id)

    @property
    def uri(self):
        return f'/images/{self.image_id}.jpeg'

    def serialize(self):
        return {
            'id': self.image_id,
            'image': self.uri,
            'modified': falcon.dt_to_http(self.modified),
            'size': self.size,
        }


class Store:

    def __init__(self, config):
        self.config = config
        self._images = {}

    def _load_from_bytes(self, data):
        return PIL.Image.open(io.BytesIO(data))

    def _convert(self, image):
        rgb_image = image.convert('RGB')

        converted = io.BytesIO()
        rgb_image.save(converted, 'JPEG')
        return converted.getvalue()

    def get(self, image_id):
        return self._images.get(image_id)

    def list_images(self):
        return sorted(self._images.values(), key=lambda item: item.modified)

    async def save(self, image_id, data):
        loop = asyncio.get_running_loop()
        image = await loop.run_in_executor(None, self._load_from_bytes, data)
        converted = await loop.run_in_executor(None, self._convert, image)

        path = os.path.join(self.config.storage_path, image_id)
        async with aiofiles.open(path, 'wb') as output:
            await output.write(converted)

        stored = Image(self.config, image_id, image.size)
        self._images[image_id] = stored
        return stored
