import falcon
import falcon.uri


class RawPathComponent:
    def process_request(self, req, resp):
        raw_uri = req.env.get('RAW_URI') or req.env.get('REQUEST_URI')

        # NOTE: Reconstruct the percent-encoded path from the raw URI.
        if raw_uri:
            req.path, _, _ = raw_uri.partition('?')


class URLResource:
    def on_get(self, req, resp, url):
        # NOTE: url here is potentially percent-encoded.
        url = falcon.uri.decode(url)

        resp.media = {'url': url}

    def on_get_status(self, req, resp, url):
        # NOTE: url here is potentially percent-encoded.
        url = falcon.uri.decode(url)

        resp.media = {'cached': True}


app = falcon.App(middleware=[RawPathComponent()])
app.add_route('/cache/{url}', URLResource())
app.add_route('/cache/{url}/status', URLResource(), suffix='status')
