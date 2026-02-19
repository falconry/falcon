import falcon.asgi

from .config import Config
from .images import Images
from .store import Store


def create_app(config=None):
    config = config or Config()
    store = Store(config)
    images = Images(config, store)

    app = falcon.asgi.App()
    app.add_route('/images', images)
    app.add_route('/images/{image_id:uuid}.jpeg', images, suffix='image')

    return app
