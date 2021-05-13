import asyncio
import datetime
import io

import aiofiles
import falcon
import PIL.Image


class Image:
    def __init__(self, config, image_id, size):
        self._config = config

        self.image_id = image_id
        self.size = size
        self.modified = datetime.datetime.utcnow()

    @property
    def path(self):
        return self._config.storage_path / self.image_id

    @property
    def uri(self):
        return f'/images/{self.image_id}.jpeg'

    def serialize(self):
        return {
            'id': self.image_id,
            'image': self.uri,
            'modified': falcon.dt_to_http(self.modified),
            'size': self.size,
            'thumbnails': self.thumbnails(),
        }

    def thumbnails(self):
        def reductions(size, min_size):
            width, height = size
            factor = 2
            while width // factor >= min_size and height // factor >= min_size:
                yield (width // factor, height // factor)
                factor *= 2

        return [
            f'/thumbnails/{self.image_id}/{width}x{height}.jpeg'
            for width, height in reductions(self.size, self._config.min_thumb_size)
        ]


class Store:
    def __init__(self, config):
        self._config = config
        self._images = {}

    def _load_from_bytes(self, data):
        return PIL.Image.open(io.BytesIO(data))

    def _convert(self, image):
        rgb_image = image.convert('RGB')

        converted = io.BytesIO()
        rgb_image.save(converted, 'JPEG')
        return converted.getvalue()

    def _resize(self, data, size):
        image = PIL.Image.open(io.BytesIO(data))
        image.thumbnail(size)

        resized = io.BytesIO()
        image.save(resized, 'JPEG')
        return resized.getvalue()

    def get(self, image_id):
        return self._images.get(image_id)

    def list_images(self):
        return sorted(self._images.values(), key=lambda item: item.modified)

    async def make_thumbnail(self, image, size):
        async with aiofiles.open(image.path, 'rb') as img_file:
            data = await img_file.read()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._resize, data, size)

    async def save(self, image_id, data):
        loop = asyncio.get_running_loop()
        image = await loop.run_in_executor(None, self._load_from_bytes, data)
        converted = await loop.run_in_executor(None, self._convert, image)

        path = self._config.storage_path / image_id
        async with aiofiles.open(path, 'wb') as output:
            await output.write(converted)

        stored = Image(self._config, image_id, image.size)
        self._images[image_id] = stored
        return stored
