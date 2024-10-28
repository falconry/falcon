from __future__ import annotations

from typing import Any, Iterable, Optional, Union

from .request import Request
from .response import Response


class CORSMiddleware(object):
    """CORS Middleware.

    This middleware provides a simple out-of-the box CORS policy, including handling
    of preflighted requests from the browser.

    See also:

    * https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    * https://www.w3.org/TR/cors/#resource-processing-model

    Note:
        Falcon will automatically add OPTIONS responders if they are missing from the
        responder instances added to the routes. When providing a custom ``on_options``
        method, the ``Allow`` headers in the response should be set to the allowed
        method values. If the ``Allow`` header is missing from the response,
        this middleware will deny the preflight request.

        This is also valid when using a sink function.

    Keyword Arguments:
        allow_origins (Union[str, Iterable[str]]): List of origins to allow (case
            sensitive). The string ``'*'`` acts as a wildcard, matching every origin.
            (default ``'*'``).
        expose_headers (Optional[Union[str, Iterable[str]]]): List of additional
            response headers to expose via the ``Access-Control-Expose-Headers``
            header. These headers are in addition to the CORS-safelisted ones:
            ``Cache-Control``, ``Content-Language``, ``Content-Length``,
            ``Content-Type``, ``Expires``, ``Last-Modified``, ``Pragma``.
            (default ``None``).

            See also:
            https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Access-Control-Expose-Headers
        allow_credentials (Optional[Union[str, Iterable[str]]]): List of origins
            (case sensitive) for which to allow credentials via the
            ``Access-Control-Allow-Credentials`` header.
            The string ``'*'`` acts as a wildcard, matching every allowed origin,
            while ``None`` disallows all origins. This parameter takes effect only
            if the origin is allowed by the ``allow_origins`` argument.
            (Default ``None``).

    """

    def __init__(
        self,
        allow_origins: Union[str, Iterable[str]] = '*',
        expose_headers: Optional[Union[str, Iterable[str]]] = None,
        allow_credentials: Optional[Union[str, Iterable[str]]] = None,
    ):
        if allow_origins == '*':
            self.allow_origins = allow_origins
        else:
            if isinstance(allow_origins, str):
                allow_origins = [allow_origins]
            self.allow_origins = frozenset(allow_origins)
            if '*' in self.allow_origins:
                raise ValueError(
                    'The wildcard string "*" may only be passed to allow_origins as a '
                    'string literal, not inside an iterable.'
                )

        if expose_headers is not None and not isinstance(expose_headers, str):
            expose_headers = ', '.join(expose_headers)
        self.expose_headers = expose_headers

        if allow_credentials is None:
            allow_credentials = frozenset()
        elif allow_credentials != '*':
            if isinstance(allow_credentials, str):
                allow_credentials = [allow_credentials]
            allow_credentials = frozenset(allow_credentials)
            if '*' in allow_credentials:
                raise ValueError(
                    'The wildcard string "*" may only be passed to allow_credentials '
                    'as a string literal, not inside an iterable.'
                )
        self.allow_credentials = allow_credentials

    def process_response(
        self, req: Request, resp: Response, resource: object, req_succeeded: bool
    ) -> None:
        """Implement the CORS policy for all routes.

        This middleware provides a simple out-of-the box CORS policy,
        including handling of preflighted requests from the browser.

        See also: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS

        See also: https://www.w3.org/TR/cors/#resource-processing-model
        """

        origin = req.get_header('Origin')
        if origin is None:
            return

        if self.allow_origins != '*' and origin not in self.allow_origins:
            return

        if resp.get_header('Access-Control-Allow-Origin') is None:
            set_origin = '*' if self.allow_origins == '*' else origin
            if self.allow_credentials == '*' or origin in self.allow_credentials:
                set_origin = origin
                resp.set_header('Access-Control-Allow-Credentials', 'true')
            resp.set_header('Access-Control-Allow-Origin', set_origin)

        if self.expose_headers:
            resp.set_header('Access-Control-Expose-Headers', self.expose_headers)

        if (
            req_succeeded
            and req.method == 'OPTIONS'
            and req.get_header('Access-Control-Request-Method')
        ):
            # NOTE(kgriffs): This is a CORS preflight request. Patch the
            #   response accordingly.

            allow = resp.get_header('Allow')
            resp.delete_header('Allow')

            allow_headers = req.get_header(
                'Access-Control-Request-Headers', default='*'
            )

            if allow is None:
                # there is no allow set, remove all access control headers
                resp.delete_header('Access-Control-Allow-Methods')
                resp.delete_header('Access-Control-Allow-Headers')
                resp.delete_header('Access-Control-Max-Age')
                resp.delete_header('Access-Control-Expose-Headers')
                resp.delete_header('Access-Control-Allow-Origin')
            else:
                resp.set_header('Access-Control-Allow-Methods', allow)
                resp.set_header('Access-Control-Allow-Headers', allow_headers)
                resp.set_header('Access-Control-Max-Age', '86400')  # 24 hours

    async def process_response_async(self, *args: Any) -> None:
        self.process_response(*args)
