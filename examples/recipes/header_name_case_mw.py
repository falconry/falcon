from collections.abc import Callable
from collections.abc import Iterable
from typing import Any, Optional


class CustomHeadersMiddleware:
    def __init__(
        self,
        app: Callable[..., Iterable[bytes]],
        title_case: bool = True,
        custom_capitalization: Optional[dict[str, str]] = None,
    ) -> None:
        self._app = app
        self._title_case = title_case
        self._capitalization = custom_capitalization or {}

    def __call__(
        self, environ: dict[str, Any], start_response: Callable[..., Any]
    ) -> Iterable[bytes]:
        def start_response_wrapper(
            status: str,
            response_headers: list[tuple[str, str]],
            exc_info: Optional[tuple[Any, Any, Any]] = None,
        ) -> Any:
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
