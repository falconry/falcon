import os
import uuid


class Config:
    DEFAULT_CONFIG_PATH = '/tmp/asgilook'
    DEFAULT_UUID_GENERATOR = uuid.uuid4

    def __init__(self):
        self.storage_path = (os.environ.get('ASGI_LOOK_STORAGE_PATH')
                             or self.DEFAULT_CONFIG_PATH)
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

        self.uuid_generator = Config.DEFAULT_UUID_GENERATOR
