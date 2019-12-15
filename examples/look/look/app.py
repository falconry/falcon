import os

import falcon

from .images import ImageStore, Resource


def create_app(image_store):
    image_resource = Resource(image_store)
    app = falcon.App()
    app.add_route('/images', image_resource)
    return app


def get_app():
    storage_path = os.environ.get('LOOK_STORAGE_PATH', '.')
    image_store = ImageStore(storage_path)
    return create_app(image_store)
