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

"""WSGI start_response mock.

This module implements a callable StartResponseMock class that can be
used, along with a mock environ dict, to simulate a WSGI request.
"""

from __future__ import annotations

from typing import Any, Optional

from falcon import util
from falcon._typing import HeaderIter
from falcon.typing import Headers


class StartResponseMock:
    """Mock object representing a WSGI `start_response` callable."""

    status: Optional[str]
    """HTTP status line, e.g. '785 TPS Cover Sheet not attached'."""
    headers: Optional[HeaderIter]
    """Raw headers list passed to `start_response`, per PEP-3333."""
    headers_dict: Headers
    """Headers as a case-insensitive ``dict``-like object, instead of a ``list``."""

    def __init__(self) -> None:
        self._called = 0
        self.status = None
        self.headers = None
        self.exc_info: Optional[Any] = None

    def __call__(
        self,
        status: str,
        headers: HeaderIter,
        exc_info: Optional[Any] = None,
    ) -> Any:
        """Implement the PEP-3333 `start_response` protocol."""

        self._called += 1
        self.status = status

        # NOTE(kgriffs): Normalize headers to be lowercase regardless
        # of what Falcon returns, so asserts in tests don't have to
        # worry about the case-insensitive nature of header names.
        self.headers = [(name.lower(), value) for name, value in headers]

        self.headers_dict = util.CaseInsensitiveDict(headers)  # type: ignore[assignment]
        self.exc_info = exc_info

    @property
    def call_count(self) -> int:
        """Number of times `start_response` was called."""
        return self._called
