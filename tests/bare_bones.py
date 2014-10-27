import falcon


class Things(object):
    def on_get(self, req, resp):
        pass


api = application = falcon.API()
api.add_route('/', Things())


if __name__ == '__main__':
    # import eventlet.wsgi
    # import eventlet
    # eventlet.wsgi.server(eventlet.listen(('localhost', 8000)), application)

    from wsgiref.simple_server import make_server
    server = make_server('localhost', 8000, application)
    server.serve_forever()
