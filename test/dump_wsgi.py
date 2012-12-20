def application(environ, start_response):
    start_response("200 OK", [('Content-Type', 'text/plain')])

    body = '\n{\n'
    for key, value in environ.items():
        if isinstance(value, basestring):
            body += '    "{0}": "{1}",\n'.format(key, value)

    body += '}\n\n'

    return body

import gevent, gevent.wsgi

server = gevent.wsgi.WSGIServer(('localhost', 8000), application)
server.serve_forever()
