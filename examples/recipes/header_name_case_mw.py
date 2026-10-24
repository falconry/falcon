from __future__ import annotations

from collections.abc import Callable
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wsgiref.types import StartResponse
    from wsgiref.types import WSGIApplication
    from wsgiref.types import WSGIEnvironment

    from _typeshed import OptExcInfo


class CustomHeadersMiddleware:
    def __init__(
        self,
        app: WSGIApplication,
        title_case: bool = True,
        custom_capitalization: dict[str, str] | None = None,
    ) -> None:
        self._app = app
        self._title_case = title_case
        self._capitalization = custom_capitalization or {}

    def __call__(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> Iterable[bytes]:
        def start_response_wrapper(
            status: str,
            response_headers: list[tuple[str, str]],
            exc_info: OptExcInfo | None = None,
        ) -> Callable[[bytes], object]:
            if self._title_case:
                headers = [
                    (self._capitalization.get(name, name.title()), value)
                    for name, value in response_headers
                ]
            else:
                headers = [
                    (self._capitalization.get(name, name), value)
                    for name, value in response_headers
                ]
            return start_response(status, headers, exc_info)

        return self._app(environ, start_response_wrapper)
