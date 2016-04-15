def application(environ, start_response):
    # wsgi_errors = environ['wsgi.errors']

    start_response('200 OK', [
        ('Content-Type', 'text/plain')])

    body = '\n{\n'
    for key, value in environ.items():
        # if isinstance(value, str):
        body += '    "{0}": "{1}",\n'.format(key, value)

    body += '}\n\n'

    return [body.encode('utf-8')]

app = application


if __name__ == '__main__':
    # import eventlet.wsgi
    # import eventlet
    # eventlet.wsgi.server(eventlet.listen(('localhost', 8000)), application)

    from wsgiref.simple_server import make_server
    server = make_server('localhost', 8000, application)
    server.serve_forever()
