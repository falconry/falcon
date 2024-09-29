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

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from falcon.util import http_status_to_code

if TYPE_CHECKING:
    from falcon._typing import HeaderArg
    from falcon._typing import ResponseStatus


class HTTPStatus(Exception):
    """Represents a generic HTTP status.

    Raise an instance of this class from a hook, middleware, or
    responder to short-circuit request processing in a manner similar
    to ``falcon.HTTPError``, but for non-error status codes.

    Args:
        status (Union[str,int]): HTTP status code or line (e.g.,
            ``'400 Bad Request'``). This may be set to a member of
            :class:`http.HTTPStatus`, an HTTP status line string or byte
            string (e.g., ``'200 OK'``), or an ``int``.
        headers (dict): Extra headers to add to the response.
        text (str): String representing response content. Falcon will encode
            this value as UTF-8 in the response.
    """

    __slots__ = ('status', 'headers', 'text')

    status: ResponseStatus
    """The HTTP status line or integer code for the status that this exception
    represents.
    """
    headers: Optional[HeaderArg]
    """Extra headers to add to the response."""
    text: Optional[str]
    """String representing response content.
    Falcon will encode this value as UTF-8 in the response.
    """

    def __init__(
        self,
        status: ResponseStatus,
        headers: Optional[HeaderArg] = None,
        text: Optional[str] = None,
    ) -> None:
        self.status = status
        self.headers = headers
        self.text = text

    @property
    def status_code(self) -> int:
        """HTTP status code normalized from :attr:`status`."""
        return http_status_to_code(self.status)
