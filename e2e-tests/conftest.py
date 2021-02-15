import pathlib
import subprocess
import time

import pytest
import requests

import falcon.testing


HERE = pathlib.Path(__file__).resolve().parent
INDEX = '/static/index.html'


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

    # NOTE(vytas): give Unicorn a rather generous time period to stop since it
    #   is waiting for the browser to close open connections such as WS & SSE.
    uvicorn.communicate(timeout=30)


@pytest.fixture()
def browser(sb, base_url):
    sb.open(base_url + INDEX)
    return sb
