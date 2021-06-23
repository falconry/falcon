import os
import pathlib
import uuid

import aioredis


class Config:
    DEFAULT_CONFIG_PATH = '/tmp/asgilook'
    DEFAULT_MIN_THUMB_SIZE = 64
    DEFAULT_REDIS_HOST = 'redis://localhost'
    DEFAULT_REDIS_POOL = aioredis.create_redis_pool
    DEFAULT_UUID_GENERATOR = uuid.uuid4

    def __init__(self):
        self.storage_path = pathlib.Path(
            os.environ.get('ASGI_LOOK_STORAGE_PATH', self.DEFAULT_CONFIG_PATH)
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.create_redis_pool = Config.DEFAULT_REDIS_POOL
        self.min_thumb_size = self.DEFAULT_MIN_THUMB_SIZE
        self.redis_host = self.DEFAULT_REDIS_HOST
        self.uuid_generator = Config.DEFAULT_UUID_GENERATOR
