def application(environ, start_response):
    start_response("200 OK", [('Content-Type', 'text/plain')])

    body = '\n{\n'
    for key in environ:
        body += '    "{0}": "{1}",\n'.format(key, environ[key])

    body += '}\n\n'

    return body
