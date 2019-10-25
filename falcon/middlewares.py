
class CORSMiddleware(object):
    def process_response(self, req, resp, resource, req_succeeded):
        """Implement a simple blanket CORS policy for all routes.

        This middleware provides a simple out-of-the box CORS policy,
        including handling of preflighted requests from the browser.

        See also: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
        """

        if resp.get_header('Access-Control-Allow-Origin') is None:
            resp.set_header('Access-Control-Allow-Origin', '*')

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
