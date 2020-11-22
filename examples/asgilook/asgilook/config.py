import os
import uuid

import aioredis


class Config:
    DEFAULT_CONFIG_PATH = '/tmp/asgilook'
    DEFAULT_MIN_THUMB_SIZE = 64
    DEFAULT_REDIS_HOST = 'redis://localhost'
    DEFAULT_REDIS_POOL = aioredis.create_redis_pool
    DEFAULT_UUID_GENERATOR = uuid.uuid4

    def __init__(self):
        self.storage_path = (os.environ.get('ASGI_LOOK_STORAGE_PATH')
                             or self.DEFAULT_CONFIG_PATH)
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)  # pragma: nocover

        self.create_redis_pool = Config.DEFAULT_REDIS_POOL
        self.min_thumb_size = self.DEFAULT_MIN_THUMB_SIZE
        self.redis_host = self.DEFAULT_REDIS_HOST
        self.uuid_generator = Config.DEFAULT_UUID_GENERATOR
