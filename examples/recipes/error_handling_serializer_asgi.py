import falcon.asgi


def serialize_error(req, resp, exception):
    preferred = req.client_prefers((falcon.MEDIA_JSON, falcon.MEDIA_TEXT))

    if preferred == falcon.MEDIA_TEXT:
        report = ['[Custom error serializer]\n']
        for key, value in sorted(exception.to_dict().items()):
            report.append(f'{key}: {value}\n')

        resp.content_type = falcon.MEDIA_TEXT
        resp.text = ''.join(report)
    else:
        resp.content_type = falcon.MEDIA_JSON
        resp.data = exception.to_json()

    resp.append_header('Vary', 'Accept')


class Division:
    async def on_get(self, req, resp, dividend, divisor):
        resp.media = dividend / divisor


app = falcon.asgi.App()
app.set_error_serializer(serialize_error)
app.add_route('/division/{dividend:int}/{divisor:int}', Division())
