import contextvars
from typing import Optional


class _Context:
    def __init__(self) -> None:
        self._request_id_var: contextvars.ContextVar[Optional[str]] = (
            contextvars.ContextVar('request_id', default=None)
        )

    @property
    def request_id(self) -> Optional[str]:
        return self._request_id_var.get()

    @request_id.setter
    def request_id(self, value: str) -> None:
        self._request_id_var.set(value)


ctx = _Context()
