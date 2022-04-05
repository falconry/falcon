from typing import Callable
from typing import Iterable
from typing import Optional
from typing import Union

from .request import Request
from .response import Response


OriginFilter = Callable[[str], bool]

class CORSMiddleware(object):
    """CORS Middleware.

    This middleware provides a simple out-of-the box CORS policy, including handling
    of preflighted requests from the browser.

    See also:

    * https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    * https://www.w3.org/TR/cors/#resource-processing-model

    Keyword Arguments:
        allow_origins (Union[str, Iterable[str]]): List of origins to allow (case
            sensitive) or callable. The string ``'*'`` acts as a wildcard, matching every origin.
            (default ``'*'``).
        expose_headers (Optional[Union[str, Iterable[str]]]): List of additional
            response headers to expose via the ``Access-Control-Expose-Headers``
            header. These headers are in addition to the CORS-safelisted ones:
            ``Cache-Control``, ``Content-Language``, ``Content-Length``,
            ``Content-Type``, ``Expires``, ``Last-Modified``, ``Pragma``.
            (default ``None``).

            See also:
            https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Access-Control-Expose-Headers
        allow_credentials (Optional[Union[str, Iterable[str], OriginFilter]]): List of origins
            (case sensitive) or callable for which to allow credentials via the
            ``Access-Control-Allow-Credentials`` header.
            The string ``'*'`` acts as a wildcard, matching every allowed origin,
            while ``None`` disallows all origins. This parameter takes effect only
            if the origin is allowed by the ``allow_origins`` argument.
            (Default ``None``).

    """

    def __init__(
        self,
        allow_origins: Union[str, Iterable[str], OriginFilter] = '*',
        expose_headers: Optional[Union[str, Iterable[str]]] = None,
        allow_credentials: Optional[Union[str, Iterable[str], OriginFilter]] = None,
    ):
        self.allow_origins_wildcard = False
        if isinstance(allow_origins, Callable):
            self.allow_origins_filter = allow_origins
        else:
            if allow_origins == '*':
                self.allow_origins_wildcard = True
            else:
                if isinstance(allow_origins, str):
                    allow_origins = [allow_origins]
                allow_origins = frozenset(allow_origins)
                if '*' in allow_origins:
                    raise ValueError(
                        'The wildcard string "*" may only be passed to allow_origins as a '
                        'string literal, not inside an iterable.'
                    )
            self.allow_origins_filter = self.create_origin_filter(allow_origins)

        if expose_headers is not None and not isinstance(expose_headers, str):
            expose_headers = ', '.join(expose_headers)
        self.expose_headers = expose_headers

        if isinstance(allow_credentials, Callable):
            self.allow_credentials_filter = allow_credentials
        else:
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
            self.allow_credentials_filter = self.create_origin_filter(allow_credentials)

    def create_origin_filter(self, allow_list):
        def filter_func(origin):
            if allow_list == '*' or origin in allow_list:
                return True
            return False
        return filter_func

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

        if not self.allow_origins_filter(origin):
            return

        if resp.get_header('Access-Control-Allow-Origin') is None:
            set_origin = '*' if self.allow_origins_wildcard else origin
            if self.allow_credentials_filter(origin):
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

            resp.set_header('Access-Control-Allow-Methods', allow)
            resp.set_header('Access-Control-Allow-Headers', allow_headers)
            resp.set_header('Access-Control-Max-Age', '86400')  # 24 hours

    async def process_response_async(self, *args):
        self.process_response(*args)
