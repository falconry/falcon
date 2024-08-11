import falcon.asgi
import falcon.uri


class RawPathComponent:
    async def process_request(self, req, resp):
        raw_path = req.scope.get('raw_path')

        # NOTE: Decode the raw path from the raw_path bytestring, disallowing
        #   non-ASCII characters, assuming they are correctly percent-coded.
        if raw_path:
            req.path = raw_path.decode('ascii')


class URLResource:
    async def on_get(self, req, resp, url):
        # NOTE: url here is potentially percent-encoded.
        url = falcon.uri.decode(url)

        resp.media = {'url': url}

    async def on_get_status(self, req, resp, url):
        # NOTE: url here is potentially percent-encoded.
        url = falcon.uri.decode(url)

        resp.media = {'cached': True}


app = falcon.asgi.App(middleware=[RawPathComponent()])
app.add_route('/cache/{url}', URLResource())
app.add_route('/cache/{url}/status', URLResource(), suffix='status')
