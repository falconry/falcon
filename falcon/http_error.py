import json

from .status_codes import *


class HTTPError(Exception):
    """Represents a generic HTTP error.

    Raise this or a child class to have Falcon automagically return pretty
    error responses (with an appropriate HTTP status code) to the client
    when something goes wrong.

    """

    __slots__ = ('status', 'title', 'description', 'href', 'code')

    def __init__(self, status, title, description,
                 href=None, href_rel=None, href_text=None,
                 code=None):

        self.status = status
        self.title = title
        self.description = description
        self.code = code

        if href:
            self.link = {
                'href': href,
                'rel': href_rel or 'help',
                'text': href_text or 'API documention for this error'
            }
        else:
            self.link = None

    def json(self):
        obj = {
            'title': self.title,
            'description': self.description,
        }

        if self.code:
            obj['code'] = self.code

        if self.link:
            obj['link'] = self.link

        return json.dumps(obj)

