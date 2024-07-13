import os
import subprocess
import sys
import time

import requests

LOOK_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

gunicorn = None


def pytest_sessionstart(session):
    global gunicorn

    gunicorn = subprocess.Popen(
        (
            sys.executable,
            '-m',
            'gunicorn',
            '--pythonpath',
            LOOK_PATH,
            'look.app:get_app()',
        ),
        env=dict(os.environ, LOOK_STORAGE_PATH='/tmp'),
    )

    # NOTE(vytas): give Gunicorn some time to start.
    for attempt in range(3):
        try:
            requests.get('http://127.0.0.1/images', timeout=1)
            break
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.2)


def pytest_sessionfinish(session, exitstatus):
    gunicorn.terminate()
    gunicorn.communicate()
