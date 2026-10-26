from __future__ import annotations

import contextvars


class _Context:
    def __init__(self) -> None:
        self._request_id_var: contextvars.ContextVar[str | None] = (
            contextvars.ContextVar('request_id', default=None)
        )

    @property
    def request_id(self) -> str | None:
        return self._request_id_var.get()

    @request_id.setter
    def request_id(self, value: str | None) -> None:
        self._request_id_var.set(value)


ctx = _Context()
