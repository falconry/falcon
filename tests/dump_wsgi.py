import pdb
from wsgiref.simple_server import make_server
import eventlet.wsgi
import eventlet

def application(environ, start_response):
    wsgi_errors = environ['wsgi.errors']

    start_response("200 OK", [
        ('Content-Type', 'text/plain')])

    body = '\n{\n'
    for key, value in environ.items():
        # if isinstance(value, str):
        body += '    "{0}": "{1}",\n'.format(key, value)

    body += '}\n\n'

    return [body]

app = application


if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('localhost', 8000)), application)
    # server = make_server('localhost', 8000, application)
    # server.serve_forever()
