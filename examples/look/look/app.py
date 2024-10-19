import os

import falcon

from .images import Collection
from .images import ImageStore
from .images import Item


def create_app(image_store):
    app = falcon.App()
    app.add_route('/images', Collection(image_store))
    app.add_route('/images/{name}', Item(image_store))
    return app


def get_app():
    storage_path = os.environ.get('LOOK_STORAGE_PATH', '.')
    image_store = ImageStore(storage_path)
    return create_app(image_store)
