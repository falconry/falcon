from __future__ import annotations

import aiofiles

import falcon

from .config import Config
from .store import Store


class Images:
    def __init__(self, config: Config, store: Store) -> None:
        self._config = config
        self._store = store

    async def on_get(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        resp.media = [image.serialize() for image in self._store.list_images()]

    async def on_get_image(self, req: falcon.asgi.Request, resp: falcon.asgi.Response, image_id: str) -> None:
        # NOTE: image_id: UUID is converted back to a string identifier.
        image = self._store.get(str(image_id))
        if not image:
            raise falcon.HTTPNotFound

        resp.stream = await aiofiles.open(image.path, 'rb')
        resp.content_type = falcon.MEDIA_JPEG

    async def on_post(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        data = await req.stream.read()
        image_id = str(self._config.uuid_generator())
        image = await self._store.save(image_id, data)

        resp.location = image.uri
        resp.media = image.serialize()
        resp.status = falcon.HTTP_201


class Thumbnails:
    def __init__(self, store: Store) -> None:
        self._store = store

    async def on_get(self, req: falcon.asgi.Request, resp: falcon.asgi.Response, image_id: str, width: int, height: int) -> None:
        image = self._store.get(str(image_id))
        if not image:
            raise falcon.HTTPNotFound
        if req.path not in image.thumbnails():
            raise falcon.HTTPNotFound

        resp.content_type = falcon.MEDIA_JPEG
        resp.data = await self._store.make_thumbnail(image, (width, height))
