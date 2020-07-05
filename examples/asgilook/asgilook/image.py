import aiofiles
import falcon


class Images:

    def __init__(self, config, store):
        self.config = config
        self.store = store

    async def on_get(self, req, resp):
        resp.media = [image.serialize() for image in self.store.list_images()]

    async def on_get_image(self, req, resp, image_id):
        image = self.store.get(str(image_id))
        resp.stream = await aiofiles.open(image.path, 'rb')
        resp.content_type = falcon.MEDIA_JPEG

    async def on_post(self, req, resp):
        data = await req.stream.read()
        image_id = str(self.config.uuid_generator())
        image = await self.store.save(image_id, data)

        resp.location = image.uri
        resp.media = image.serialize()
        resp.status = falcon.HTTP_201
