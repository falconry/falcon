# middleware.py

from uuid import uuid4

# Optional logging package (pip install structlog)
import structlog


class RequestIDMiddleware:
    def process_request(self, req, resp):
        request_id = str(uuid4())

        # Using Falcon 2.0 syntax
        req.context.request_id = request_id

        # Or if your logger has built-in support for contexts
        req.context.log = structlog.get_logger(request_id=request_id)

    # It may also be helpful to include the ID in the response
    def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('X-Request-ID', req.context.request_id)
