import aiofiles

import falcon


class Images:
    def __init__(self, config, store):
        self._config = config
        self._store = store

    async def on_get(self, req, resp):
        resp.media = [image.serialize() for image in self._store.list_images()]

    async def on_get_image(self, req, resp, image_id):
        # NOTE: image_id: UUID is converted back to a string identifier.
        image = self._store.get(str(image_id))
        resp.stream = await aiofiles.open(image.path, 'rb')
        resp.content_type = falcon.MEDIA_JPEG

    async def on_post(self, req, resp):
        data = await req.stream.read()
        image_id = str(self._config.uuid_generator())
        image = await self._store.save(image_id, data)

        resp.location = image.uri
        resp.media = image.serialize()
        resp.status = falcon.HTTP_201