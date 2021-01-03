import pathlib
import subprocess
import time

import pytest
import requests

import falcon.testing


HERE = pathlib.Path(__file__).resolve().parent


@pytest.fixture(scope='session')
def base_url():
    port = falcon.testing.get_unused_port()
    base_url = f'http://127.0.0.1:{port}'

    uvicorn = subprocess.Popen(
        ('uvicorn', '--port', str(port), 'server:app'),
        cwd=HERE,
    )

    # NOTE(vytas): give Uvicorn some time to start.
    for attempt in range(3):
        try:
            resp = requests.get(f'{base_url}/ping', timeout=1)
            resp.raise_for_status()
            break
        except requests.exceptions.RequestException:
            pass
        time.sleep(attempt + 0.5)
    else:
        pytest.fail('Could not start Uvicorn')

    yield base_url

    uvicorn.terminate()
    uvicorn.communicate(timeout=5)


@pytest.fixture()
def browser(sb, base_url):
    sb.open(base_url + '/ping')
    return sb
