import falcon


# Import or copy CustomHeadersMiddleware from the above snippet
class CustomHeadersMiddleware: ...


class FunkyResource:
    def on_get(self, req, resp):
        resp.set_header('X-Funky-Header', 'test')
        resp.media = {'message': 'Hello'}


app = falcon.App()
app.add_route('/test', FunkyResource())

app = CustomHeadersMiddleware(
    app,
    custom_capitalization={'x-funky-header': 'X-FuNkY-HeADeR'},
)
