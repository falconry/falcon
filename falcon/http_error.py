# Copyright 2013 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""HTTPError exception class."""

import json
import xml.etree.ElementTree as et

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict

from falcon.util import uri


class HTTPError(Exception):
    """Represents a generic HTTP error.

    Raise this or a child class to have Falcon automagically return pretty
    error responses (with an appropriate HTTP status code) to the client
    when something goes wrong.

    Attributes:
        status (str): HTTP status line, e.g. '748 Confounded by Ponies'.
        has_representation (bool): Read-only property that determines
            whether error details will be serialized when composing
            the HTTP response. In ``HTTPError`` this property always
            returns ``True``, but child classes may override it
            in order to return ``False`` when an empty HTTP body is desired.
            See also the ``falcon.http_error.NoRepresentation`` mixin.
        title (str): Error title to send to the client.
        description (str): Description of the error to send to the client.
        headers (dict): Extra headers to add to the response.
        link (str): An href that the client can provide to the user for
            getting help.
        code (int): An internal application code that a user can reference when
            requesting support for the error.

    Args:
        status (str): HTTP status code and text, such as "400 Bad Request"

    Keyword Args:
        title (str): Human-friendly error title. If not provided, defaults
            to the HTTP status line as determined by the ``status`` argument.
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two (default ``None``).
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.

        headers (dict): Extra headers to return in the
            response to the client (default ``None``).
        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'API documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).
    """

    __slots__ = (
        'status',
        'title',
        'description',
        'headers',
        'link',
        'code',
    )

    def __init__(self, status, title=None, description=None, headers=None,
                 href=None, href_text=None, code=None):
        self.status = status

        # TODO(kgriffs): HTTP/2 does away with the "reason phrase". Eventually
        #   we'll probably switch over to making everything code-based to more
        #   easily support HTTP/2. When that happens, should we continue to
        #   include the reason phrase in the title?
        self.title = title or status

        self.description = description
        self.headers = headers
        self.code = code

        if href:
            link = self.link = OrderedDict()
            link['text'] = (href_text or 'Documentation related to this error')
            link['href'] = uri.encode(href)
            link['rel'] = 'help'
        else:
            self.link = None

    @property
    def has_representation(self):
        return True

    def to_dict(self, obj_type=dict):
        """Returns a basic dictionary representing the error.

        This method can be useful when serializing the error to hash-like
        media types, such as YAML, JSON, and MessagePack.

        Args:
            obj_type: A dict-like type that will be used to store the
                error information (default ``dict``).

        Returns:
            dict: A dictionary populated with the error's title,
            description, etc.

        """

        obj = obj_type()

        obj['title'] = self.title

        if self.description is not None:
            obj['description'] = self.description

        if self.code is not None:
            obj['code'] = self.code

        if self.link is not None:
            obj['link'] = self.link

        return obj

    def to_json(self):
        """Returns a pretty-printed JSON representation of the error.

        Returns:
            str: A JSON document for the error.

        """

        obj = self.to_dict(OrderedDict)
        return json.dumps(obj, indent=4, separators=(',', ': '),
                          ensure_ascii=False)

    def to_xml(self):
        """Returns an XML-encoded representation of the error.

        Returns:
            str: An XML document for the error.

        """

        error_element = et.Element('error')

        et.SubElement(error_element, 'title').text = self.title

        if self.description is not None:
            et.SubElement(error_element, 'description').text = self.description

        if self.code is not None:
            et.SubElement(error_element, 'code').text = str(self.code)

        if self.link is not None:
            link_element = et.SubElement(error_element, 'link')

            for key in ('text', 'href', 'rel'):
                et.SubElement(link_element, key).text = self.link[key]

        return (b'<?xml version="1.0" encoding="UTF-8"?>' +
                et.tostring(error_element, encoding='utf-8'))


class NoRepresentation(object):
    """Mixin for ``HTTPError`` child classes that have no representation.

    This class can be mixed in when inheriting from ``HTTPError``, in order
    to override the `has_representation` property such that it always
    returns ``False``. This, in turn, will cause Falcon to return an empty
    response body to the client.

    You can use this mixin when defining errors that either should not have
    a body (as dictated by HTTP standards or common practice), or in the
    case that a detailed error response may leak information to an attacker.

    Note:
        This mixin class must appear before ``HTTPError`` in the base class
        list when defining the child; otherwise, it will not override the
        `has_representation` property as expected.

    """

    @property
    def has_representation(self):
        return False


class OptionalRepresentation(object):
    """Mixin for ``HTTPError`` child classes that may have a representation.

    This class can be mixed in when inheriting from ``HTTPError`` in order
    to override the `has_representation` property, such that it will
    return ``False`` when the error instance has no description
    (i.e., the `description` kwarg was not set).

    You can use this mixin when defining errors that do not include
    a body in the HTTP response by default, serializing details only when
    the web developer provides a description of the error.

    Note:
        This mixin class must appear before ``HTTPError`` in the base class
        list when defining the child; otherwise, it will not override the
        `has_representation` property as expected.

    """
    @property
    def has_representation(self):
        return super(OptionalRepresentation, self).description is not None
