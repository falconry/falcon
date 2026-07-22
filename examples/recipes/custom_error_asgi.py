import falcon
import falcon.asgi


class AlreadyRunningError(Exception):
    def __init__(self, taskid):
        self.taskid = taskid


async def handle_already_running(req, resp, exception, params):
    raise falcon.HTTPConflict(
        title=f'Task {exception.taskid} already running!', description=str(exception)
    )


def serialize_error(req, resp, exception):
    data = exception.to_dict()

    resp.media = {
        'success': False,
        'error': {
            'http_status': exception.status,
            'title': data.get('title'),
            'message': 'Custom Error Serializer',
        },
    }

    resp.content_type = falcon.MEDIA_JSON


class Start:
    async def on_get(self, req, resp, taskid):
        raise AlreadyRunningError(taskid)


app = falcon.asgi.App()

app.add_error_handler(AlreadyRunningError, handle_already_running)
app.set_error_serializer(serialize_error)

app.add_route('/start/{taskid:int}', Start())
