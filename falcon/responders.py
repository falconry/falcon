from .status_codes import *


def path_not_found(req, resp):
    resp.status = HTTP_404

def bad_request(req, resp):
    resp.status = HTTP_400

def create_method_not_allowed(allowed_methods):
    def method_not_allowed(req, resp):
        resp.status = HTTP_405
        resp.set_header('Allow', ', '.join(allowed_methods))

    return method_not_allowed
