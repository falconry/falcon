import falcon
import falcon.media


class Forms:
    def on_post(self, req, resp):
        example = {}
        for part in req.media:
            if part.content_type.startswith('multipart/mixed'):
                for nested in part.media:
                    example[nested.filename] = nested.text

        resp.media = example


parser = falcon.media.MultipartFormHandler()
parser.parse_options.media_handlers['multipart/mixed'] = (
    falcon.media.MultipartFormHandler()
)

app = falcon.App()
app.req_options.media_handlers[falcon.MEDIA_MULTIPART] = parser
app.add_route('/forms', Forms())
