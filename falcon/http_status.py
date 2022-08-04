# Copyright 2015 by Hurricane Labs LLC
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

"""HTTPStatus exception class."""

from falcon.util.deprecation import RemovedError


class HTTPStatus(Exception):
    """Represents a generic HTTP status.

    Raise an instance of this class from a hook, middleware, or
    responder to short-circuit request processing in a manner similar
    to ``falcon.HTTPError``, but for non-error status codes.

    Args:
        status (str): HTTP status code and text, such as
            '748 Confounded by Ponies'.
        headers (dict): Extra headers to add to the response.
        text (str): String representing response content. Falcon will encode
            this value as UTF-8 in the response.

    Attributes:
        status (str): HTTP status line, e.g. '748 Confounded by Ponies'.
        headers (dict): Extra headers to add to the response.
        text (str): String representing response content. Falcon will encode
            this value as UTF-8 in the response.

    """

    __slots__ = ('status', 'headers', 'text')

    def __init__(self, status, headers=None, text=None):
        self.status = status
        self.headers = headers
        self.text = text

    @property  # type: ignore
    def body(self):
        raise RemovedError(
            'The body attribute is no longer supported. '
            'Please use the text attribute instead.'
        )
