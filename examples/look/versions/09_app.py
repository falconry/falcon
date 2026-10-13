import falcon

from .images import ImageStore
from .images import Resource


def create_app(image_store):
    image_resource = Resource(image_store)
    app = falcon.App()
    app.add_route('/images', image_resource)
    return app


def get_app():
    image_store = ImageStore('.')
    return create_app(image_store)
