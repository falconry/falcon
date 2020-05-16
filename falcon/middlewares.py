from typing import Iterable, Optional, Union

from .request import Request
from .response import Response


class CORSMiddleware(object):
    """CORS Middleware

    This middleware provides a simple out-of-the box CORS policy, including handling
    of preflighted requests from the browser.

    See also:

    * https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    * https://www.w3.org/TR/cors/#resource-processing-model

    Keyword Arguments:
        allow_origin (Union[str, Iterable[str]]): List of origins to allow (case
            sensitive). The string ``'*'`` acts as a wildcard, matching every origin.
            (default ``'*'``).
        expose_headers (Optional[Union[str, Iterable[str]]]): List of additional headers to
            expose. (default ``None``).
        allow_credentials (Union[bool, Iterable[str]]): List of origins to allow credentials (case
            sensitive). When ``True`` allows credentials for each allowed origin. This has effect
            only if the origin is allowed by the ``allow_origin`` argument. (default ``False``).
    """
    def __init__(
        self,
        allow_origin: Union[str, Iterable[str]] = '*',
        expose_headers: Optional[Union[str, Iterable[str]]] = None,
        allow_credentials: Union[bool, Iterable[str]] = False
    ):
        if allow_origin == '*':
            self.allow_origin = allow_origin
        else:
            if isinstance(allow_origin, str):
                allow_origin = [allow_origin]
            self.allow_origin = frozenset(allow_origin)

        if expose_headers is not None and not isinstance(expose_headers, str):
            expose_headers = ', '.join(expose_headers)
        self.expose_headers = expose_headers

        if allow_credentials is False:
            allow_credentials = frozenset()
        elif allow_credentials is not True:
            allow_credentials = frozenset(allow_credentials)
        self.allow_credentials = allow_credentials

    def process_response(self, req: Request, resp: Response, resource, req_succeeded):
        """Implement the CORS policy for all routes.

        This middleware provides a simple out-of-the box CORS policy,
        including handling of preflighted requests from the browser.

        See also: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS

        See also: https://www.w3.org/TR/cors/#resource-processing-model
        """

        origin = req.get_header('Origin')
        if origin is None:
            return

        if self.allow_origin != '*' and origin not in self.allow_origin:
            return

        if resp.get_header('Access-Control-Allow-Origin') is None:
            set_origin = '*' if self.allow_origin == '*' else origin
            if self.allow_credentials is True or origin in self.allow_credentials:
                set_origin = origin
                resp.set_header('Access-Control-Allow-Credentials', 'true')
            resp.set_header('Access-Control-Allow-Origin', set_origin)

        if self.expose_headers:
            resp.set_header('Access-Control-Expose-Headers', self.expose_headers)

        if (req_succeeded and
                req.method == 'OPTIONS' and
                req.get_header('Access-Control-Request-Method')):

            # NOTE(kgriffs): This is a CORS preflight request. Patch the
            #   response accordingly.

            allow = resp.get_header('Allow')
            resp.delete_header('Allow')

            allow_headers = req.get_header('Access-Control-Request-Headers', default='*')

            resp.set_header('Access-Control-Allow-Methods', allow)
            resp.set_header('Access-Control-Allow-Headers', allow_headers)
            resp.set_header('Access-Control-Max-Age', '86400')  # 24 hours

    async def process_response_async(self, *args):
        self.process_response(*args)
