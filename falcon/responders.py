from falcon.status_codes import *


def path_not_found(ctx, req, resp):
    resp.status = HTTP_404

def bad_request(ctx, req, resp):
    resp.status = HTTP_400

def create_method_not_allowed(allowed_methods):
    def method_not_allowed(ctx, req, resp):
        resp.status = HTTP_405
        resp.set_header('Allow', ', '.join(allowed_methods))

    return method_not_allowed
