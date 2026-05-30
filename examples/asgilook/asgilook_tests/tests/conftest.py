import io
import random
import uuid

import fakeredis.aioredis
import PIL.Image
import PIL.ImageDraw
import pytest

import falcon.asgi
import falcon.testing

from asgilook.app import create_app
from asgilook.config import Config


@pytest.fixture()
def predictable_uuid():
    fixtures = (
        uuid.UUID('36562622-48e5-4a61-be67-e426b11821ed'),
        uuid.UUID('3bc731ac-8cd8-4f39-b6fe-1a195d3b4e74'),
        uuid.UUID('ba1c4951-73bc-45a4-a1f6-aa2b958dafa4'),
    )

    def uuid_func():
        try:
            return next(fixtures_it)
        except StopIteration:
            return uuid.uuid4()

    fixtures_it = iter(fixtures)
    return uuid_func


@pytest.fixture(scope='session')
def storage_path(tmpdir_factory):
    return tmpdir_factory.mktemp('asgilook')


@pytest.fixture
def client(predictable_uuid, storage_path):
    # NOTE(vytas): Unlike the sync FakeRedis, fakeredis.aioredis.FakeRedis
    #   seems to share a global state in 2.17.0 (by design or oversight).
    #   Make sure we initialize a new fake server for every test case.
    def fake_redis_from_url(*args, **kwargs):
        server = fakeredis.FakeServer()
        return fakeredis.aioredis.FakeRedis(server=server)

    config = Config()
    config.redis_from_url = fake_redis_from_url
    config.redis_host = 'redis://localhost'
    config.storage_path = storage_path
    config.uuid_generator = predictable_uuid

    app = create_app(config)
    return falcon.testing.TestClient(app)


@pytest.fixture(scope='session')
def png_image():
    image = PIL.Image.new('RGBA', (640, 360), color='black')

    draw = PIL.ImageDraw.Draw(image)
    for _ in range(32):
        x0 = random.randint(20, 620)
        y0 = random.randint(20, 340)
        x1 = random.randint(20, 620)
        y1 = random.randint(20, 340)
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        draw.ellipse([(x0, y0), (x1, y1)], fill='yellow', outline='red')

    output = io.BytesIO()
    image.save(output, 'PNG')
    return output.getvalue()


@pytest.fixture(scope='session')
def image_size():
    def report_size(data):
        image = PIL.Image.open(io.BytesIO(data))
        return image.size

    return report_size
