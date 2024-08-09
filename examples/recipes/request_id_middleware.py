# middleware.py

from uuid import uuid4

from context import ctx


class RequestIDMiddleware:
    def process_request(self, req, resp):
        ctx.request_id = str(uuid4())

    # It may also be helpful to include the ID in the response
    def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('X-Request-ID', ctx.request_id)
