import pytest
from wslook.app import app

import falcon.testing


@pytest.fixture()
def client():
    return falcon.testing.TestClient(app)
