def application(environ, start_response):
    # wsgi_errors = environ['wsgi.errors']

    start_response('200 OK', [
        ('Content-Type', 'text/plain')])

    body = '\n{\n'
    for key, value in environ.items():
        # if isinstance(value, str):
        body += '    "{0}": "{1}",\n'.format(key, value)

    body += '}\n\n'

    if not isinstance(body, bytes):
        body = body.encode('utf-8')

    return [body]


app = application


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    server = make_server('localhost', 8000, application)

    print('Listening on localhost:8000...')

    server.serve_forever()
