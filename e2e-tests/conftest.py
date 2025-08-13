# Copyright 2020-2025 by Vytautas Liuolia.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
# NOTE(vytas): sb here is seleniumbase's pytest fixture, see also
#   "The sb pytest fixture (no class)" at
#   https://seleniumbase.io/help_docs/syntax_formats/.
def browser(sb, base_url):
    sb.open(base_url + INDEX)

    sb.assert_text('SSE CONNECTED', 'div.sse', timeout=5)
    sb.remove_elements('div.message')

    return sb


@pytest.fixture()
def clear_log(browser):
    def _impl():
        browser.remove_elements('div.message')

    return _impl
