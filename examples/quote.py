import falcon


class QuoteResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle GET requests."""
        resp.media = {
            'quote': "I've always been more interested in the future than in the past.",
            'author': 'Grace Hopper',
        }


app = falcon.App()
app.add_route('/quote', QuoteResource())
