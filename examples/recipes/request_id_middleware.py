# middleware.py

from uuid import uuid4

from context import ctx


class RequestIDMiddleware:
    def process_request(self, req, resp):
        request_id = str(uuid4())
        ctx.request_id = request_id
        req.context.request_id = request_id

    # It may also be helpful to include the ID in the response
    def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('X-Request-ID', ctx.request_id)
