import falcon

from .images import ImageStore
from .images import Resource

app = application = falcon.App()

image_store = ImageStore('.')
images = Resource(image_store)
app.add_route('/images', images)
