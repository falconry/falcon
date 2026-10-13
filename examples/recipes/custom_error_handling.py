import falcon


def serialize_error(req, resp, exception):
    """Serialize HTTPError using the client's preferred media type."""
    preferred = req.client_prefers((falcon.MEDIA_JSON, falcon.MEDIA_TEXT))
    if preferred == falcon.MEDIA_JSON:
        resp.content_type = preferred
        resp.data = exception.to_json()
    else:
        report = ['[Custom error serializer]\n']
        for key, value in sorted(exception.to_dict().items()):
            report.append(f'{key}: {value}\n')

        resp.content_type = falcon.MEDIA_TEXT
        resp.text = ''.join(report)

    resp.append_header('Vary', 'Accept')


def handle_overflow(req, resp, ex, params):
    """Handle OverflowError from responders (e.g. extreme exponentiation)."""
    if 'power' in params and params['power'] >= 1000:
        # Reraise as HTTPError so the error serializer formats the response
        raise falcon.HTTPBadRequest(title='Too Damn High!')

    # Or render a custom error response directly
    resp.content_type = falcon.MEDIA_TEXT
    resp.text = 'That was too much to handle... Check your parameters.\n'
    resp.status = falcon.HTTP_UNPROCESSABLE_ENTITY


class Division:
    def on_get(self, req, resp, dividend, divisor):
        # Divide by 0 makes Falcon return a generic 500 via the default handler
        resp.media = dividend / divisor


class Exponentiation:
    def on_get(self, req, resp, base, power):
        resp.media = base**power


app = falcon.App()

app.add_error_handler(OverflowError, handle_overflow)
app.set_error_serializer(serialize_error)

app.add_route('/division/{dividend:float}/{divisor:float}', Division())
app.add_route('/exponentiation/{base:float}/{power:float}', Exponentiation())
