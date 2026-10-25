import falcon


class AlreadyRunningError(Exception):
    def __init__(self, taskid):
        self.taskid = taskid

    @staticmethod
    def handle(req, resp, ex, params):
        raise falcon.HTTPConflict(
            title=f'Task {ex.taskid} already running!', description=str(ex)
        )


def serialize_error(req, resp, exception):
    message = 'Custom Error Serializer'
    data = exception.to_dict()
    prefered_media = req.client_prefers((falcon.MEDIA_JSON,))
    if prefered_media is not None:
        resp.media = {
            'success': False,
            'error': {
                'http_status': exception.status,
                'title': data.get('title'),
                'message': message,
            },
        }
        resp.content_type = falcon.MEDIA_JSON
    else:
        resp.text = f'{message}\n{exception.status}\n{data.get("title")}\n'
        resp.content_type = falcon.MEDIA_TEXT
    resp.append_header('Vary', 'Accept')


class Start:
    def on_get(self, req, resp, taskid):
        raise AlreadyRunningError(taskid)


app = falcon.App()

app.add_error_handler(AlreadyRunningError)
app.set_error_serializer(serialize_error)

app.add_route('/start/{taskid:int}', Start())
