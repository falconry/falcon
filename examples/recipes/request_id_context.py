# context.py

import threading


class _Context:
    def __init__(self):
        self._thread_local = threading.local()

    @property
    def request_id(self):
        return getattr(self._thread_local, 'request_id', None)

    @request_id.setter
    def request_id(self, value):
        self._thread_local.request_id = value


ctx = _Context()
