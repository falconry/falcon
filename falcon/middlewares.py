
class CORSMiddleware(object):
    def process_response(self, req, resp, resource, req_succeeded):
        """
        CORS Middleware out of the box in falcon to turn on/off the CORS
        Headers on preflight validation from the browser.

        Args:
            req: Current request object to check method was used.
            resp: Current response object to add headers for CORS if
                they does not exists
            resource:
            req_succeeded: Flag to check if the response was handled
                successfully or there have been an error
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

            allow_headers = req.get_header(
                'Access-Control-Request-Headers',
                default='*'
            )

            resp.set_header('Access-Control-Allow-Methods', allow)
            resp.set_header('Access-Control-Allow-Headers', allow_headers)
            resp.set_header('Access-Control-Max-Age', '86400')  # 24 hours
