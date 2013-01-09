import re

QS_PATTERN = re.compile(r'([a-zA-Z_]+)=([^&]+)')


def parse_query_string(query_string):
    # Parse query string
    # PERF: use for loop in lieu of the dict constructor
    params = {}
    for k, v in QS_PATTERN.findall(query_string):
        if ',' in v:
            v = v.split(',')

        params[k] = v

    return params


def parse_headers(env):
    # Parse HTTP_*
    headers = {}
    for key in env:
        if key.startswith('HTTP_'):
            headers[key[5:]] = env[key]

    # Per the WSGI spec, Content-Type is not under HTTP_*
    if 'CONTENT_TYPE' in env:
        headers['CONTENT_TYPE'] = env['CONTENT_TYPE']

    # Per the WSGI spec, Content-Length is not under HTTP_*
    if 'CONTENT_LENGTH' in env:
        headers['CONTENT_LENGTH'] = env['CONTENT_LENGTH']

    # Fallback to SERVER_* vars if the Host header isn't specified
    if 'HOST' not in headers:
        host = env['SERVER_NAME']
        port = env['SERVER_PORT']

        if port != '80':
            host = ''.join([host, ':', port])

        headers['HOST'] = host

    return headers
