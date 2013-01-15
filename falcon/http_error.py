"""Defines the HTTPError class.

Copyright 2013 by Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

from .status_codes import *


class HTTPError(Exception):
    """Represents a generic HTTP error.

    Raise this or a child class to have Falcon automagically return pretty
    error responses (with an appropriate HTTP status code) to the client
    when something goes wrong.

    """

    __slots__ = (
        'status',
        'title',
        'description',
        'headers',
        'link',
        'code'
    )

    def __init__(self, status, title, description, headers=None,
                 href=None, href_rel=None, href_text=None, code=None):
        """Initialize with information that can be reported to the client

        Falcon will catch instances of HTTPError (and subclasses), then use
        the associated information to generate a nice response for the client.

        Args:
            status: HTTP status code and text, such as "400 Bad Request"
            title: Human-friendly error title. Set to None if you wish Falcon
                to return an empty response body (all remaining args will
                be ignored.) Do this only when you don't wish to disclose
                sensitive information about why a request was refused.
            description: Human-friendly description of the error, along with a
                helpful suggestion or two. Must be set to None if title is
                set to None.
            headers: A dictionary of extra headers to return in the
                response to the client (default None).
            href: A URL someone can visit to find out more information
                (default None).
            href_rel: If href is given, this is value to use for the rel
                attribute (default 'doc').
            href_text: Friendly title/description for the link (defaults to
                "API documentation for this error").
            code: An internal code that customers can reference in their
                support request or to help them when searching for knowledge
                base articles related to this error.

        """

        self.headers = headers
        self.status = status
        self.title = title
        self.description = description
        self.code = code

        if href:
            self.link = {
                'href': href,
                'rel': href_rel or 'doc',
                'text': href_text or 'API documention for this error'
            }
        else:
            self.link = None

    def json(self):
        """Returns a pretty JSON-encoded version of the exception

        Note: Excludes the HTTP status line, since the results of this call
        are meant to be returned in the body of an HTTP response.

        Returns:
            A JSON representation of the exception except the status line, or
            NONE if title was set to None.

        """

        if self.title is None:
            return None

        # Serialize by hand to enforce ordering, making it nice for humans
        obj = (
            '{\n'
            '    "title": "%s",\n'
            '    "description": "%s"'
        ) % (self.title, self.description)

        if self.code:
            obj += (
                ',\n'
                '    "code": "%s"'
            ) % self.code

        if self.link:
            obj += (
                ',\n'
                '    "link":  {\n'
                '        "text": "%s",\n'
                '        "href": "%s",\n'
                '        "rel": "%s"\n'
                '    }'
            ) % (self.link['text'], self.link['href'], self.link['rel'])

        obj += '\n}'

        return obj
