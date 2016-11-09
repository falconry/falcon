import os

import falcon
from .images import ImageSaver, Resource


def create_app(image_saver):
    image_resource = Resource(image_saver)
    api = falcon.API()
    api.add_route('/images', image_resource)
    return api


def get_app():
    storage_path = os.environ.get('LOOK_STORAGE', '.')
    image_saver = ImageSaver(storage_path)
    return create_app(image_saver)
