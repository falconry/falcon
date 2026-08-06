from __future__ import annotations

import asyncio
import datetime
import io
from pathlib import Path
from typing import Any

import aiofiles
import PIL.Image

import falcon

from .config import Config


class Image:
    def __init__(self, config: Config, image_id: str, size: tuple[int, int]) -> None:
        self._config = config

        self.image_id = image_id
        self.size = size
        self.modified = datetime.datetime.now(datetime.timezone.utc)

    @property
    def path(self) -> Path:
        return Path(self._config.storage_path) / self.image_id

    @property
    def uri(self) -> str:
        return f'/images/{self.image_id}.jpeg'

    def serialize(self) -> dict[str, Any]:
        return {
            'id': self.image_id,
            'image': self.uri,
            'modified': falcon.dt_to_http(self.modified),
            'size': self.size,
            'thumbnails': self.thumbnails(),
        }

    def thumbnails(self) -> list[str]:
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
    def __init__(self, config: Config) -> None:
        self._config = config
        self._images: dict[str, Image] = {}

    def _load_from_bytes(self, data: bytes) -> PIL.Image.Image:
        return PIL.Image.open(io.BytesIO(data))

    def _convert(self, image: PIL.Image.Image) -> bytes:
        rgb_image = image.convert('RGB')

        converted = io.BytesIO()
        rgb_image.save(converted, 'JPEG')
        return converted.getvalue()

    def _resize(self, data: bytes, size: tuple[int, int]) -> bytes:
        image = PIL.Image.open(io.BytesIO(data))
        image.thumbnail(size)

        resized = io.BytesIO()
        image.save(resized, 'JPEG')
        return resized.getvalue()

    def get(self, image_id: str) -> Image | None:
        return self._images.get(image_id)

    def list_images(self) -> list[Image]:
        return sorted(self._images.values(), key=lambda item: item.modified)

    async def make_thumbnail(self, image: Image, size: tuple[int, int]) -> bytes:
        async with aiofiles.open(image.path, 'rb') as img_file:
            data = await img_file.read()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._resize, data, size)

    async def save(self, image_id: str, data: bytes) -> Image:
        loop = asyncio.get_running_loop()
        image = await loop.run_in_executor(None, self._load_from_bytes, data)
        converted = await loop.run_in_executor(None, self._convert, image)

        path = self._config.storage_path / image_id
        async with aiofiles.open(path, 'wb') as output:
            await output.write(converted)

        stored = Image(self._config, image_id, image.size)
        self._images[image_id] = stored
        return stored
