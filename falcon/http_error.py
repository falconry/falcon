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

import json
import sys

if sys.version_info < (2, 7):  # pragma: no cover
    # NOTE(kgriffs): We could use the module from PyPI, but ordering isn't
    # critical in JSON, and Falcon eschews dependencies.
    OrderedDict = dict
else:  # pragma: no cover
    from collections import OrderedDict

from falcon import util


class HTTPError(Exception):
    """Represents a generic HTTP error.

    Raise this or a child class to have Falcon automagically return pretty
    error responses (with an appropriate HTTP status code) to the client
    when something goes wrong.

    Attributes:
        status: HTTP status line, such as "748 Confounded by Ponies".
        title: Error title to send to the client.
        description: Description of the error to send to the client.
        headers: A dictionary of extra headers to add to the response.
        link: An href that the client can provide to the user for getting help.
        code: An internal application code that a user can reference when
            requesting support for the error.

    """

    __slots__ = (
        'status',
        'title',
        'description',
        'headers',
        'link',
        'code'
    )

    def __init__(self, status, title, description=None, headers=None,
                 href=None, href_text=None, code=None):
        """Initialize with information that can be reported to the client

        Falcon will catch instances of HTTPError (and subclasses), then use
        the associated information to generate a nice response for the client.

        Args:
            status: HTTP status code and text, such as "400 Bad Request"
            title: Human-friendly error title. Set to None if you wish Falcon
                to return an empty response body (all remaining args will
                be ignored except for headers.) Do this only when you don't
                wish to disclose sensitive information about why a request was
                refused, or if the status and headers are self-descriptive.
            description: Human-friendly description of the error, along with a
                helpful suggestion or two (default None).
            headers: A dictionary of extra headers to return in the
                response to the client (default None).
            href: A URL someone can visit to find out more information
                (default None). Unicode characters are percent-encoded.
            href_text: If href is given, use this as the friendly
                title/description for the link (defaults to "API documentation
                for this error").
            code: An internal code that customers can reference in their
                support request or to help them when searching for knowledge
                base articles related to this error.

        """

        self.status = status
        self.title = title
        self.description = description
        self.headers = headers
        self.code = code

        if href:
            link = self.link = OrderedDict()
            link['text'] = (href_text or 'API documention for this error')
            link['href'] = util.percent_escape(href)
            link['rel'] = 'help'
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

        obj = OrderedDict()
        obj['title'] = self.title

        if self.description:
            obj['description'] = self.description

        if self.code:
            obj['code'] = self.code

        if self.link:
            obj['link'] = self.link

        return json.dumps(obj, indent=4, separators=(',', ': '),
                          ensure_ascii=False)
