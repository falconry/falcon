import falcon.asgi

from .cache import RedisCache
from .config import Config
from .images import Images
from .images import Thumbnails
from .store import Store


def create_app(config=None):
    config = config or Config()
    cache = RedisCache(config)
    store = Store(config)
    images = Images(config, store)
    thumbnails = Thumbnails(store)

    app = falcon.asgi.App(middleware=[cache])
    app.add_route('/images', images)
    app.add_route('/images/{image_id:uuid}.jpeg', images, suffix='image')
    app.add_route(
        '/thumbnails/{image_id:uuid}/{width:int}x{height:int}.jpeg', thumbnails
    )

    return app
