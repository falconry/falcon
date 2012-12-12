from status_codes import *

def path_not_found_handler(ctx):
    ctx.resp_status = HTTP_404
    ctx.resp_body = ''
