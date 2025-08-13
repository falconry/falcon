import contextvars


class _Context:
    def __init__(self):
        self._request_id_var = contextvars.ContextVar('request_id', default=None)

    @property
    def request_id(self):
        return self._request_id_var.get()

    @request_id.setter
    def request_id(self, value):
        self._request_id_var.set(value)


ctx = _Context()
