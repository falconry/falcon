from status_codes import *

def path_not_found_handler(ctx, req, resp):
    resp['status'] = HTTP_404
