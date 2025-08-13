from datetime import datetime
from datetime import timezone
from functools import partial
from http import HTTPStatus
from typing import Annotated, Any
import uuid

import msgspec

import falcon
from falcon import Request
from falcon import Response
from falcon.media import JSONHandler


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Note(msgspec.Struct):
    text: Annotated[str, msgspec.Meta(max_length=256)]
    noteid: uuid.UUID = msgspec.field(default_factory=uuid.uuid4)
    created: datetime = msgspec.field(
        default_factory=partial(datetime.now, timezone.utc)
    )


class NoteResource:
    POST_SCHEMA = Note

    def __init__(self) -> None:
        # NOTE: In a real-world app, you would want to use persistent storage.
        self._store: dict[str, Note] = {}

    def on_get_note(self, req: Request, resp: Response, noteid: uuid.UUID) -> None:
        resp.media = self._store.get(str(noteid))
        if not resp.media:
            raise falcon.HTTPNotFound(
                description=f'Note with {noteid=} is not in the store.'
            )

    def on_delete_note(self, req: Request, resp: Response, noteid: uuid.UUID) -> None:
        self._store.pop(str(noteid), None)
        resp.status = HTTPStatus.NO_CONTENT

    def on_get(self, req: Request, resp: Response) -> None:
        resp.media = self._store

    def on_post(self, req: Request, resp: Response, note: Note) -> None:
        self._store[str(note.noteid)] = note
        resp.location = f'{req.path}/{note.noteid}'
        resp.media = note
        resp.status = HTTPStatus.CREATED


class MsgspecMiddleware:
    def process_resource(
        self, req: Request, resp: Response, resource: object, params: dict[str, Any]
    ) -> None:
        if schema := getattr(resource, f'{req.method}_SCHEMA', None):
            param = schema.__name__.lower()
            params[param] = msgspec.convert(req.get_media(), schema)


def _handle_validation_error(
    req: Request, resp: Response, ex: msgspec.ValidationError, params: dict[str, Any]
) -> None:
    raise falcon.HTTPUnprocessableEntity(description=str(ex))


def create_app() -> falcon.App:
    app = falcon.App(middleware=[MsgspecMiddleware()])
    app.add_error_handler(msgspec.ValidationError, _handle_validation_error)

    json_handler = JSONHandler(
        dumps=msgspec.json.encode,
        loads=msgspec.json.decode,
    )
    app.req_options.media_handlers[falcon.MEDIA_JSON] = json_handler
    app.resp_options.media_handlers[falcon.MEDIA_JSON] = json_handler

    notes = NoteResource()
    app.add_route('/notes', notes)
    app.add_route('/notes/{noteid:uuid}', notes, suffix='note')

    return app


application = create_app()
